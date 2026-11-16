"""Build the local gallery sample. Usage: python3 scripts/import_gallery.py (requires Pillow)."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from io import BytesIO
from urllib.parse import quote
import csv
import hashlib
import json
import subprocess

from PIL import Image, ImageOps

root = Path(__file__).resolve().parent.parent
workspace = root.parent
for folder in ['media', 'originals']:
    (root / folder).mkdir(exist_ok=True)

def parse(name):
    with (root/'scripts'/name).open() as file:
        return list(csv.reader(file, delimiter='\t'))

def fetch(url):
    result = subprocess.run(
        ['curl','-fLsS','--retry','1','--max-time','23',url],
        capture_output=True,
    )
    if result.returncode != 0:
        raise ValueError(url)
    return result.stdout

index = json.loads(fetch('https://xiaosang.cc/data/repos.json'))
links = {p['name']:p.get('homepage') for section in index['categories'] for p in section['repos'] if not p.get('hidden')}
series = {}
for slug, repo, title, style, prompt in parse('series.tsv'):
    series[slug] = dict(id=slug, repo=repo, title=title, style=style, url=links[repo], template=prompt, works=[])

exts = {'PNG':'png', 'WEBP':'webp', 'JPEG':'jpg', 'AVIF':'avif', 'GIF':'gif'}
woodcut_bounds = {
    'mountain': (60,61,59,75),
    'wukang': (60,58,50,57),
    'kyoto': (53,54,50,51),
}

def sources(profile, path):
    if path.startswith('local:'):
        yield workspace/path[6:]
        return
    if path.startswith('https://'):
        yield path
        return
    repo = profile['repo']
    local = workspace / repo / path
    if local.is_file():
        yield local
    encoded = quote(path, safe='/')
    yield f'https://raw.githubusercontent.com/holynova/{repo}/HEAD/{encoded}'
    yield f'https://media.githubusercontent.com/media/holynova/{repo}/HEAD/{encoded}'

def read_asset(profile,path):
    for source in sources(profile,path):
        try:
            content = source.read_bytes() if isinstance(source,Path) else fetch(source)
            with Image.open(BytesIO(content)) as file:
                file.load()
                return content, ImageOps.exif_transpose(file).copy(), exts[file.format]
        except (ValueError,OSError,KeyError) as error:
            print('retry:', str(source), str(error), flush=True)
    raise ValueError(f"{profile['repo']} / {path}")

def import_work(row):
    group,key,title,path,quality,category,scene,palette=row
    profile=series[group]
    name=group+'-'+key
    content, picture, ext = read_asset(profile,path)
    width,height = picture.size
    if picture.mode not in ['RGB','RGBA']:
        picture=picture.convert('RGBA' if 'transparency' in picture.info else 'RGB')
    original = f'originals/{name}.{ext}'
    (root/original).write_bytes(content)
    box=[0,0,width,height]
    preview=picture
    if group=='woodcut':
        left,right,top,bottom=woodcut_bounds[key]
        left,right=round(left*width/960),round(right*width/960)
        top,bottom=round(top*height/1200),round(bottom*height/1200)
        box=[left,top,width-left-right,height-top-bottom]
        preview=picture.crop((left,top,width-right,height-bottom))
    variants={}
    for label, rendition, edge, compression in [('s',preview,420,79),('m',preview,840,82),('detail',picture,1680,86)]:
        image=rendition.copy()
        image.thumbnail((edge,edge),Image.Resampling.LANCZOS)
        dest=f'media/{name}-{label}.webp'
        image.save(root/dest,format='WEBP',quality=compression,method=4)
        variants[label]=[dest,*image.size]
    print('ready:', group, title, (width,height), quality, flush=True)
    provenance=profile['url'] if path.startswith('local:') else path if path.startswith('https:') else f"https://github.com/holynova/{profile['repo']}/blob/HEAD/{quote(path,safe='/')}"
    return dict(id=name,group=group,title=title,category=category,example=[title,scene,palette],variants=variants,
                original=original,quality=quality,width=width,height=height,crop=box,source=provenance,
                sha256=hashlib.sha256(content).hexdigest())

with ThreadPoolExecutor(max_workers=10) as executor:
    for item in executor.map(import_work,parse('samples.tsv')):
        series[item['group']]['works'].append(item)
assert all(len(s['works'])==3 for s in series.values())
(root/'catalog.js').write_text('const catalog = '+json.dumps(list(series.values()),ensure_ascii=False,separators=(',',':'))+';\n')
print(len(series), 'series', sum(len(s['works']) for s in series.values()), 'works')
