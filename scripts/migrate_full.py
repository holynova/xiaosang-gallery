"""Copy exact source files and generate responsive AVIF / WebP variants.

Usage: python3 scripts/migrate_full.py full-plan.json
Reruns resume from per-image metadata and retry failures. A complete manifest is
written only when every selected source image has been verified.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import cache
from threading import Semaphore
from urllib.parse import quote, urljoin
import hashlib
import json
import os
import random
import re
import shutil
import subprocess
import sys

from PIL import Image, ImageOps, ImageFile

root=Path(__file__).resolve().parent.parent
plan=Path(sys.argv[1])
profiles=json.loads(plan.read_text())
media=root/'media/v2'
originals=root/'originals'
state=root/'.migration'
for d in [media,originals,state/'records']:
    d.mkdir(parents=True,exist_ok=True)

formats={'PNG':'png','JPEG':'jpg','WEBP':'webp','AVIF':'avif','GIF':'gif'}
encode_slots=Semaphore(4)
woodcut={ 'woodcut-mountain': (60,61,59,75), 'woodcut-wukang': (60,58,50,57), 'woodcut-kyoto': (53,54,50,51) }

def source_candidates(profile,w):
    source=w.get('url')
    if source: yield str(root.parent/source[6:]) if source.startswith('local:') else source
    path=w['path']
    local=root.parent/profile['repo']/path
    if local.is_file(): yield str(local)
    escaped=quote(path,safe='/')
    if profile['id'] not in ['woodcut','gouache','toys','textbook','city']:
        public_path=re.sub(r'^(public|dist)/','',escaped)
        yield urljoin(profile['url'],public_path)
    yield f'https://raw.githubusercontent.com/holynova/{profile["repo"]}/HEAD/{escaped}'
    if profile['id']=='jade': yield f'https://holynova.github.io/jade-relief-cards/{escaped}'
    if profile['id']=='textbook': yield urljoin(profile['url'],escaped)
    yield f'https://media.githubusercontent.com/media/holynova/{profile["repo"]}/HEAD/{escaped}'

def receive(profile,w,tmp):
    existing=next((f for f in originals.glob(w['id']+'.*') if f.is_file()),None)
    if existing: return existing,'previous local source'
    errors=[]
    for source in dict.fromkeys(source_candidates(profile,w)):
        try:
            if source.startswith('/'):
                local=Path(source)
                if not local.is_file(): continue
                with Image.open(local) as image: image.verify()
                return local, source
            result=subprocess.run(['curl','-LfSs','--connect-timeout','9','--max-time','65','--retry','2','--retry-delay','1','-o',str(tmp),source],capture_output=True)
            if result.returncode:
                errors.append(str(result.stderr.decode(errors='replace').strip())[:180]); continue
            with Image.open(tmp) as img: img.verify()
            return tmp,source
        except (ValueError,OSError) as e:
            errors.append(str(e))
    raise ValueError(' | '.join(errors)[-560:])

def atomic_json(f,data):
    tmp=f.with_suffix('.next')
    tmp.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')))
    tmp.replace(f)

def paper_crop(image):
    pixels=image.convert('RGB').load()
    width,height=image.size
    edges=[]
    def paper(pixel):
        r,g,b=pixel
        return r>218 and g>211 and b>176 and r-b<57 and abs(r-g)<22
    for edge in range(4):
        breadth,depth=(height,width) if edge<2 else (width,height)
        points=range(breadth//6,5*breadth//6,max(1,breadth//70))
        for depth_pixel in range(max(0,depth//11)):
            count=0
            for pos in points:
                x,y=((depth_pixel,pos),(width-1-depth_pixel,pos),(pos,depth_pixel),(pos,height-1-depth_pixel))[edge]
                if paper(pixels[x,y]):count+=1
            if count < .91*len(points):break
        else: depth_pixel=0
        edges.append(depth_pixel if depth_pixel>depth*.017 else 0)
    return edges if sum(v>0 for v in edges)>=3 else [0,0,0,0]

def crop_box(image,id,group):
    w,h=image.size
    if id in woodcut:
        left,right,top,bottom=woodcut[id]
        left,right=round(left*w/960),round(right*w/960)
        top,bottom=round(top*h/1200),round(bottom*h/1200)
    elif group=='woodcut':
        left,right,top,bottom=paper_crop(image)
    else: left=top=right=bottom=0
    return [left,top,w-left-right,h-top-bottom]

def variant(im,target_w,target_h,avif_q,webp_q,asset):
    thumb=im.copy()
    thumb.thumbnail((target_w,target_h),Image.Resampling.LANCZOS)
    options=[('avif',dict(quality=avif_q,speed=9,max_threads=1)),('webp',dict(quality=webp_q,method=2))]
    for ext,settings in options:
        path=media/(asset+'.'+ext)
        thumb.save(path,**settings)
    return [str((media/(asset+'.avif')).relative_to(root)), str((media/(asset+'.webp')).relative_to(root)), *thumb.size]

def migrate(profile,w):
    id=w['id']
    record=state/'records'/f'{id}.json'
    if record.exists():
        return json.loads(record.read_text())
    tmp=state/f'{id}.asset'
    try:
        source,location=receive(profile,w,tmp)
        with encode_slots, Image.open(source) as file:
            ext=formats[file.format]
            raw=ImageOps.exif_transpose(file)
            image=raw.convert('RGBA' if raw.mode in ('LA','RGBA') or 'transparency' in raw.info else 'RGB')
            w0,h0=image.size
            x,y,width,height=box=crop_box(image,id,profile['id'])
            list_image=image.crop((x,y,x+width,y+height)) if width!=w0 or height!=h0 else image
            text=profile['id'] in ['concept','motorcycle','relic']
            targets={
                's':variant(list_image,384,760,58 if text else 50,76,id+'-s'),
                'm':variant(list_image,642,1040,59 if text else 53,80,id+'-m'),
                'detail':variant(image,1600 if text else 1400,1700 if text else 1400,61 if text else 57,83,id+'-detail'),
            }
            safe=originals/(id+'.'+ext)
            if source!=safe:
                if source==tmp: tmp.replace(safe)
                else: shutil.copyfile(source,safe)
            data={**w,'width':w0,'height':h0,'crop':box,'variants':targets,'original':str(safe.relative_to(root)),
                  'sha256':hashlib.file_digest(safe.open('rb'),'sha256').hexdigest(), 'downloadSource':location}
            atomic_json(record,data)
            return data
    finally:
        tmp.unlink(missing_ok=True)

jobs=[(p,w) for p in profiles for w in p['works']]
# Finish a few covers from every series early, then balance remote and local targets.
priority=[(p,w) for p in profiles for w in p['works'][:3]]
rest=[(p,w) for p in profiles for w in p['works'][3:]]
random.Random(11).shuffle(rest)
failures={}
done=0
with ThreadPoolExecutor(max_workers=int(os.environ.get("GALLERY_MIGRATION_WORKERS",18))) as pool:
    futures={pool.submit(migrate,p,w):(p['id'],w['id']) for p,w in priority+rest}
    for f in as_completed(futures):
        profile,id=futures[f]
        try: f.result()
        except Exception as error:
            failures[id]=str(error)
            print('FAILED',profile,id,str(error),flush=True)
        else:
            done+=1
            if done%25==0 or done==len(jobs):
                print(f'{done}/{len(jobs)} verified',flush=True)
atomic_json(state/'failures.json',failures)
if failures:
    sys.exit(f'{len(failures)} images need attention. Existing output is reusable.')
complete=[{**p,'works':[json.loads((state/'records'/f'{w["id"]}.json').read_text()) for w in p['works']]} for p in profiles]
atomic_json(state/'complete.json',complete)
print(f'{done} / {len(jobs)} done',flush=True)
