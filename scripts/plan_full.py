"""Reconcile published source manifests into one import plan.

Input is the source audit snapshot (site HTML, repository trees and data files).
Run with the snapshot directory. No image files are downloaded here.
"""
from collections import Counter
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
import csv
import hashlib
import json
import re
import subprocess
import sys

root = Path(__file__).resolve().parent.parent
workspace = root.parent
snapshot = Path(sys.argv[1])
decoder = json.JSONDecoder()
known = json.loads((snapshot/'baseline/catalog.js').read_text().split('=',1)[1].strip().removesuffix(';'))
samples = {}
for row in csv.reader((root/'scripts/samples.tsv').open(),delimiter='\t'):
    samples[(row[0],row[3].removeprefix('local:github-latest20-review/crossover-folk-gallery/'))]=row[0]+'-'+row[1]
sources = json.loads((snapshot/'latest-portfolio.json').read_text())
urls = {p['name']: p['homepage'] for c in sources['categories'] for p in c['repos'] if p.get('homepage') and not p.get('hidden')}
profiles = {p['id']: {**p,'url': urls[p['repo']], 'works':[]} for p in known if p['id']!='podcast'}

def read(name): return (snapshot/name).read_text()
def meta(name): return json.loads(read(name))
def page(group): return read(profiles[group]['repo']+'.html')
def clean(s): return unescape(re.sub('<[^>]+>','',s)).strip()
def parse_json(source,marker):
    return decoder.raw_decode(source.split(marker,1)[1].lstrip())[0]

def paths(group, pattern):
    tree=meta(profiles[group]['repo']+'.tree')
    if tree.get('truncated'): raise RuntimeError(f'Incomplete tree for {group}')
    return [f['path'] for f in tree['tree'] if f.get('type')=='blob' and re.search(pattern,f['path'],re.I)]

def add(group,path,title,category='',post=None,quality='original',url=None,alt=None):
    identity=samples.get((group,path)) or group+'-'+hashlib.sha1(path.encode()).hexdigest()[:13]
    items=profiles[group]['works']
    items.append(dict(id=identity, path=path, title=title, category=category, post=post, quality=quality, url=url, alt=alt))

for group in ['woodcut','gouache','toys']:
    html=page(group)
    data=json.loads(re.search(r'id="gallery-manifest">(.*?)</script>',html,re.S)[1])
    labels={k:clean(v.split('<span')[0]).split('（')[0] for k,v in re.findall(r'data-collection-filter="([^"]+)"[^>]*>(.*?)</button>',html,re.S)}
    for img in data['images']:
        title=img.get('caption') or img['alt']
        key=labels.get(img['collection'],img['collection'])
        add(group,'incoming/'+img['source'],title,key,key,alt=img.get('alt'))

class FolkParser(HTMLParser):
    def __init__(self):
        super().__init__();self.level=None;self.section='';self.group='';self.buffer=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag in ('h2','h3'): self.level=tag;self.buffer=[]
        if tag=='img' and a.get('data-full'):
            group=self.group or self.section
            add('stamps',a['data-full'],a.get('alt') or Path(a['data-full']).stem,group,
                (self.section+' · '+group) if self.section!=group else group,'source')
    def handle_data(self,data):
        if self.level: self.buffer.append(data)
    def handle_endtag(self,tag):
        if tag!=self.level:return
        title=re.sub(r'（\d+幅）$','', ''.join(self.buffer).strip())
        if tag=='h2': self.section=title;self.group=''
        else: self.group=title
        self.level=None

FolkParser().feed(page('stamps'))
published=parse_json(read('crossover-data.js'),'window.ARTWORKS_DATA =')
local_cross=workspace/'github-latest20-review/crossover-folk-gallery'
local_data=parse_json((local_cross/'assets/js/data.js').read_text(),'window.ARTWORKS_DATA =')
originals={w['id']:w.get('original') for w in local_data}
for w in published:
    file=w.get('original') or originals.get(w['id'])
    existing=file and (local_cross/file).is_file()
    add('crossover',file if existing else w['image'],w['hero']+' × '+w['character'],w['theme'],w['theme'],'original' if existing else 'source',
        url="local:"+str((local_cross/file).relative_to(workspace)) if existing else urljoin(profiles['crossover']['url'],w['image']))

for c in meta('concept-data.json'):
    add('concept','dist/'+c['image'],c['title'],c['category'],alt=c.get('hook'))
for r in meta('rock-data.json'):
    add('rock','dist/assets/'+r['id']+'.png',r['name']+' · 摄影谜题',r['region'],alt=r.get('hint'))

games=parse_json(page('liveaction'),'const GAMES =')
for game in games.values():
    for item in game['items']:
        add('liveaction',item['src'],item['name'],game['name'],game['name'],alt=item.get('sub'))

# The source array uses JS literals rather than JSON.
create=read('creation-data.js')
variants=json.loads(subprocess.check_output(['node','-e',"""const fs=require('node:fs'),vm=require('node:vm');const s=fs.readFileSync(process.argv[1],'utf8');console.log(vm.runInNewContext(s+'\\nJSON.stringify(VARIATIONS)',Object.create(null),{timeout:1000}));""",str(snapshot/'creation-data.js')]))
for v in variants:
    add('creation',v['image'],v['titleCN'],v['categoryLabel'],v['categoryLabel'],'source')

rubber=parse_json(read('rubber-data.js'),'window.COLLECTIONS =')
for collection in rubber.values():
    label=collection['title']
    for item in collection['items']:
        file=item['output']
        name=item.get('city') or item.get('title') or item.get('name') or Path(file).stem
        add('rubber',file,name,label,label,alt=item.get('features'))

citynames={'beijing':'北京','shanghai':'上海','hangzhou':'杭州','suzhou':'苏州'}
city_zh={}
data_path=workspace/'city-stamp/src'
for codefile in data_path.rglob('*.tsx'):
    data=codefile.read_text()
    for m in re.finditer(r'([a-z]+-[a-z-]+)',data):
        landmark=m[1]
        for zh in re.findall(r'["\']([\u4e00-\u9fff]{2,14})["\']',data[m.end():m.end()+110]):
            city_zh.setdefault(landmark,zh)
            break
for file in paths('city',r'^public/badges/.*\.png$'):
    id=Path(file).stem
    group=citynames.get(id.split('-')[0],id.split('-')[0])
    title=city_zh.get(id) or id.replace('-',' ')
    add('city',file,title,group,group)

citypop=parse_json((workspace/'citypop-shanghai-exploration/data.js').read_text(),'const experiments =')
for w in citypop:
    phase=re.sub(r'^\d+ / ','',w.get('roundLabel','画风实验'))
    add('citypop',w['image'],w['title'],phase,phase)

daily_groups={'category-still-life':'分类静物','daily-necessities-top20':'日用单品','brand-products':'品牌去标签','fmcg-tear-labels':'快消去标签'}
daily_titles={}
daily_app=(workspace/'daily-necessities-library/app/page.tsx').read_text()
for w in re.finditer(r'''(?:name|title):\s*['"]([^'"\n]+)['"](?:(?!\}).){0,320}?(?:image|imageUrl|src):\s*['"]([^'"]+\.png)['"]''',daily_app,re.S):
    daily_titles[Path(w[2]).name]=w[1]
for file in paths('wander',r'^public/assets/(?:category-still-life|daily-necessities-top20|brand-products|fmcg-tear-labels)/[^/]+\.png$'):
    group=daily_groups[Path(file).parent.name]
    add('wander',file,daily_titles.get(Path(file).name,Path(file).stem.split('-',1)[-1].replace('-',' ')),group,group)

style=parse_json(read('styles-data.js'),'const SCENES_DATA =')
for s in style:
    label=s['title']
    for x in s.get('styles',s.get('images',s.get('variations',[]))):
        file=x.get('image') or x.get('imageUrl') or x.get('src')
        if file: add('artstyle',file,x.get('name') or x.get('title') or Path(file).stem,label,label,'source')
if not profiles['artstyle']['works']:
    scene_names={s['id']:s['title'] for s in style}
    for file in paths('artstyle',r'^images/[^/]+\.jpg$'):
        stem=Path(file).stem
        match=re.match(r'(scene_[a-z])_\d+_(.*)',stem)
        group=scene_names.get(match[1],match[1]) if match else '画风对照'
        add('artstyle',file,match[2].replace('_',' ') if match else stem,group,group,'source')

for file in paths('cutaway',r'^public/images/.*\.png$'):
    old=next((w for p in known if p['id']=='cutaway' for w in p['works'] if w['id']==samples.get(('cutaway',file))),None)
    name=old['title'] if old else Path(file).stem
    add('cutaway',file,name,'上海地标','上海地标')

printer=(workspace/'print-atlas/app.js').read_text()
for m in re.finditer(r"\{n:'\d+',name:'([^']+)'.*?person:'([^']+)',landscape:'([^']+)',sheep:'([^']+)'",printer):
    for file,kind in zip(m.groups()[1:],('人物','宫殿','绵羊')):
        add('print','assets/'+file,m[1]+' · '+kind,m[1],m[1])
for file in paths('print',r'^assets/process-.*\.png$'):
    add('print',file,Path(file).stem.replace('process-',''), '印刷工艺', '印刷工艺')

game_names={'kyoto':'京都','times-square':'时代广场','jingan':'静安寺'}
game_js=(workspace/'game-style-transfer-atlas/app/page.tsx').read_text()
game_title={}
for m in re.finditer(r"""(?:title|name):\s*['"]([^'"]+)['"],\s*(?:(?!\}).){0,420}?image:\s*['"]images/([^'"]+)['"]""",game_js,re.S):
    game_title[m[2]]=m[1]
for file in paths('gamestyle',r'^public/images/[^/]+\.png$'):
    stem=Path(file).stem
    prefix=next((p for p in game_names if stem.startswith(p+'-')),'jingan')
    key=game_names[prefix]
    name=('参考原景' if stem.endswith('-source') else game_title.get(Path(file).name) or stem.removeprefix(prefix+'-').replace('-',' '))
    add('gamestyle',file,name,key,key)

for card in re.findall(r'<article class="card">(.*?)</article>',page('textbook'),re.S):
    listed=re.findall(r'<img src="([^"]+)" alt="([^"]+)"',card)
    if not listed:continue
    label=re.sub(r'^高清课本插图_|_[0-9]+.*$','',Path(listed[0][0]).stem)
    for file,alt in listed:
        suffix='原扫描' if file.startswith('origin/') else '照片风重绘'
        add('textbook',file,label+' · '+suffix,'课文插画',label,alt=alt)
taken={w['path'] for w in profiles['textbook']['works']}
for file in paths('textbook',r'^origin/[^/]+\.(jpg|png)$'):
    if file not in taken:
        title=re.sub(r'^高清课本插图_|_\d+$','',Path(file).stem)
        add('textbook',file,title+' · 原扫描','课文插画',title)

for card in re.findall(r'<article class="frame-card[^"]*" (.*?)</article>',page('motorcycle'),re.S):
    pic=re.search(r'data-full="([^"]+)" alt="([^"]+)"',card)
    if not pic:continue
    cat=re.search(r'data-section="([^"]+)"',card)
    director=re.search(r'data-director="([^"]+)"',card)
    key=cat[1] if cat else ''
    group={'chinese':'华语导演','world':'国际导演','global':'国际导演','cat-window':'橱窗猫'}.get(key,key or '电影摄影')
    name=unescape(director[1]) if director else unescape(pic[2])
    add('motorcycle',pic[1],name,group,group,'source',urljoin(profiles['motorcycle']['url'],pic[1]),unescape(pic[2]))

for i,item in enumerate(meta('ai-data.json')['images'],1):
    folder=item.get('folder')
    category=folder if folder not in (None,'default','') else '图像实验'
    path='public/'+item['src'].lstrip('/')
    old=next((w for p in known if p['id']=='ai' for w in p['works'] if w['id']==samples.get(('ai',path))),None)
    title=old['title'] if old else item.get('title') or '画廊作品 · '+str(i).zfill(3)
    add('ai',path,title,category,None if category=='图像实验' else category,'source')

for r in meta('wenwu-data.json')['items']:
    if r.get('has_image',bool(r.get('image'))):
        add('relic',r['image'],r['name'],r['category'],r['category'],'source',alt=r.get('note'))

for w in parse_json((workspace/'jade-cards-lab/data.js').read_text(),'var CARDS='):
    add('jade','img/'+w['f']+'.webp',w['name'],w['theme'],w['theme'],'source')

for p in profiles.values():
    if not p['works']: raise RuntimeError('No art in '+p['repo'])
    unique={}
    for item in p['works']:
        unique.setdefault(item['id'],item)
    p['works']=list(unique.values())
    print(p['id'],len(p['works']),len(set(w['category'] for w in p['works'])))
print('TOTAL',sum(len(p['works']) for p in profiles.values()))
(snapshot/'full-plan.json').write_text(json.dumps(list(profiles.values()),ensure_ascii=False))
