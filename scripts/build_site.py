"""Build static entry pages and lazy collection files from the migrated assets."""
from itertools import islice, zip_longest
from pathlib import Path
import argparse
import hashlib
import html
import json
import subprocess

root=Path(__file__).resolve().parent.parent
args=argparse.ArgumentParser()
args.add_argument('--plan',type=Path)
args.add_argument('--output',type=Path,default=root)
args.add_argument('--cloudflare-static',action='store_true',help='Build a self-contained release within the Workers static file limit')
settings=args.parse_args()
out=settings.output.resolve()
out.mkdir(parents=True,exist_ok=True)
if settings.cloudflare_static and out==root:
    args.error('--cloudflare-static requires a separate --output directory')
version=json.loads((root/'package.json').read_text())['version'] if (root/'package.json').exists() else '1.0.0'
repo_url='https://github.com/holynova/xiaosang-gallery'

def release_file(relative):
    dest=out/relative
    if dest.exists(): return
    dest.parent.mkdir(parents=True,exist_ok=True)
    # Reuse the local asset inode to stage the release without a second image library.
    dest.hardlink_to(root/relative)

def release_images(profiles):
    # The shared portfolio Worker also serves all of its existing project files.
    priority=zip_longest(*(p['works'] for p in profiles))
    prioritized=(w for row in priority for w in row if w is not None)
    avif_detail={w['id'] for w in islice(prioritized, 900)}
    for p in profiles:
        for photo in p['works']:
            variants=photo['variants']
            variants['m']=variants['s']
            if photo['id'] not in avif_detail:
                variants['detail']=[variants['detail'][1],*variants['detail'][1:]]
            for f in {photo['original'], *(target for v in variants.values() for target in v[:2])}:
                release_file(f)

def load_data():
    if not settings.plan:
        return json.loads((root/'.migration/complete.json').read_text())
    planned=json.loads(settings.plan.read_text())
    def get(item):
        ar=root/'.migration/records'/f'{item["id"]}.json'
        return json.loads(ar.read_text()) if ar.exists() else None
    return [{**p,'works':[work for item in p['works'] if (work:=get(item))]} for p in planned]

def dump(obj):
    return json.dumps(obj,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')

def pack_cover(cover):
    id,_,_,w,h,_,_,mw,mh=cover
    return [id,w,h,mw,mh]

def pack_detail(work):
    return [*(work[k] for k in ('id','title','width','height','crop','quality','original')),work['variants']['detail'][0].endswith('.avif')]

def render(tag):
    return html.escape(str(tag),quote=True)

def short_id(text):
    return hashlib.sha1(text.encode()).hexdigest()[:12]

def pack(post):
    work,_,_,w,h,_,_,mw,mh=post['cover']
    return [post['id'],post['group'],post['title'],post['cat'],post['n'],post['bucket'],work,w,h,mw,mh]

data=out/'data'
data.mkdir(exist_ok=True)
meta=[]
collection_posts={}
counts=[]
cover_details={}
search_entries=[]
profiles=load_data()
if settings.cloudflare_static: release_images(profiles)
for profile in profiles:
    g=profile['id']
    photos=profile['works']
    if not photos: continue
    groups={}
    for w in photos:
        key=(w['post'] or '', '' if w['post'] else w['id'])
        groups.setdefault(key,[]).append(w)
    posts=[]
    bucket_sizes=[0]
    for (title,single),items in groups.items():
        parts=(len(items)+19)//20
        for i in range(parts):
            images=items[i*20:(i+1)*20]
            cover=images[0]
            name=title or cover['title']
            if parts>1: name+=f' · {i+1}/{parts}'
            if bucket_sizes[-1]+len(images)>54: bucket_sizes.append(0)
            bucket=len(bucket_sizes)-1
            bucket_sizes[bucket]+=len(images)
            posts.append(dict(bucket=bucket,id=g+'-'+short_id(title+single+':'+str(i)),group=g,title=name,
                              cat=cover['category'], n=len(images),
                              cover=[cover['id'],*cover['variants']['s'],*cover['variants']['m']]))
            photos_ids=[w['id'] for w in images]
            posts[-1]['photos']=photos_ids
    thin=[{k:v for k,v in p.items() if k!='photos'} for p in posts]
    meta.append({**{k:profile[k] for k in ('id','title','style','template','url','repo')},'works':len(photos),
                 'posts':len(posts),'cover':thin[0]['cover'],'cats':list(dict.fromkeys(w['category'] for w in photos))})
    collection_posts[g]=thin
    work_map={w['id']:w for w in photos}
    for post in posts:
        image=work_map[post['cover'][0]]
        cover_details[image['id']]={k:image[k] for k in ('id','title','width','height','crop','variants','quality','original')}
        search_entries.append([post['id'],' '.join(dict.fromkeys([post['title'],post['cat'],profile['title'],*(work_map[w]['title'] for w in post['photos'])]))])
    (data/(g+'-feed.js')).write_text('registerFeed('+dump(g)+','+dump([pack(p) for p in thin])+');\n')
    works={w['id']:{
        **{k:w[k] for k in ('id','title','category','width','height','crop','variants','quality','original','sha256')},
        'alt': w.get('alt') or '',
    } for w in photos}
    (data/(g+'-likes.js')).write_text('registerLikes('+dump(g)+','+dump({w:p['id'] for p in posts for w in p['photos']})+');\n')
    for bucket in range(len(bucket_sizes)):
        entries={p['id']:p['photos'] for p in posts if p['bucket']==bucket}
        members={key:works[key] for paths in entries.values() for key in paths}
        (data/(g+'-'+str(bucket)+'.js')).write_text('registerBucket('+dump(g+'-'+str(bucket))+','+dump({'photos':members,'posts':entries})+');\n')
    counts.append([g,len(photos),len(posts)])
order=['gouache','woodcut','crossover','stamps',*[s['id'] for s in meta if s['id'] not in ['gouache','woodcut','crossover','stamps']]]
feed=[item for row in zip_longest(*(collection_posts[g] for g in order if g in collection_posts)) for item in row if item]
seeds=feed[:10]

def cover_html(cover, mode):
    id,s_a,s_w,sw,sh,m_a,m_w,mw,mh=cover
    eager=mode in ['hero','eager']
    attr='src' if eager else 'data-src'
    size='(max-width: 720px) 46vw, (max-width: 1149px) 30vw, 250px'
    lcp=' fetchpriority="high"' if mode=='hero' else ''
    aset=f'{s_a} {sw}w, {m_a} {mw}w' if sw!=mw else s_a
    wset=f'{s_w} {sw}w, {m_w} {mw}w' if sw!=mw and s_w!=m_w else s_w
    if not eager and mode=='lazy':
        return f'<picture><source type="image/avif"><img width="{sw}" height="{sh}" decoding="async" data-post-cover alt=""></picture>'
    return f'<picture><source type="image/avif" {attr}set="{aset}" sizes="{size}"><img {attr}="{s_w}" {attr}set="{wset}" sizes="{size}" width="{sw}" height="{sh}" decoding="async" alt=""{lcp}></picture>'
smeta={s['id']:s for s in meta}
seed_html=[]
for i,post in enumerate(seeds):
    multi=f'<span class="stack-badge" aria-label="{post["n"]} 张图片"><svg class="icon" aria-hidden="true"><use href="#lucide-images"></use></svg>{post["n"]}</span>' if post['n']>1 else ''
    label=smeta[post['group']]['title']
    if post['cat'] and post['cat']!=post['title']: label+=' · '+post['cat']
    priority='hero' if i==0 else 'eager' if i==1 else 'lazy'
    seed_html.append(f'<button type="button" class="art-card" data-post="{post["id"]}" data-work="{post["cover"][0]}" aria-label="{render(post["title"])}"><span class="art-img">{cover_html(post["cover"],priority)}{multi}</span><span class="art-caption"><strong>{render(post["title"])}</strong><small>{render(label)}</small></span></button>')

(out/'gallery.css').write_text((root/'src/gallery.css').read_text())
(out/'gallery.js').write_text((root/'src/gallery.js').read_text())
(data/'index.js').write_text('registerIndex('+dump([pack(p) for p in feed])+');\n')
(data/'search.js').write_text('registerSearch('+dump(search_entries)+');\n')
overview=[]
for i,series in enumerate(meta):
    avatar=cover_html(series['cover'],'eager' if i<4 else 'overview')
    avatar=avatar.replace('data-src','src').replace('decoding="async"','decoding="async" loading="lazy"') if i>=4 else avatar
    overview.append(f'<a class="overview-card" href="index.html?series={series["id"]}"><span class="overview-image">{avatar}</span><span class="overview-label"><strong>{render(series["title"])}</strong><small>{series["works"]} 张 · {series["posts"]} 帖</small></span></a>')
(out/'overview.html').write_text(f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>系列总览 · xiaosang AI图集</title><link rel="icon" href="favicon.svg"><link rel="stylesheet" href="gallery.css"></head><body><header class="site-header"><div class="page-width overview-top"><a href="index.html">xiaosang AI图集</a></div></header><main class="page-width overview-page"><div class="overview-heading"><h1>系列总览</h1><p>{len(meta)} 个系列 · {sum(s['works'] for s in meta)} 张作品</p></div><div class="overview-grid">{''.join(overview)}</div><footer class="release-meta"><a href="{repo_url}">GitHub</a><span>v{version}</span></footer></main></body></html>''')

highlight=(seeds[0]['cover'] if seeds else None)
preload=''
if highlight:
    _,s,_,w,_,m,_,mw,_=highlight
    candidates=f'{s} {w}w, {m} {mw}w' if w!=mw else s
    preload=f'<link rel="preload" as="image" type="image/avif" imagesrcset="{candidates}" imagesizes="(max-width: 720px) 46vw, (max-width: 1149px) 30vw, 250px" fetchpriority="high">'
(data/'templates.js').write_text('registerTemplates('+dump({s['id']:s['template'] for s in meta})+');\n')
lean_meta=[{**{k:v for k,v in x.items() if k not in ('template','cover')},'cover':pack_cover(x['cover'])} for x in meta]
config=f'<script type="application/json" id="catalog-config">{dump({"meta":lean_meta,"seeds":[pack(p) for p in seeds],"count":len(feed),"singleWebpThumb":settings.cloudflare_static,"previews":[pack_detail(cover_details[p["cover"][0]]) for p in seeds]})}</script>'
shell=(root/'src/gallery.html').read_text()
shell=shell.replace('<!-- IMAGE_PRELOAD -->',preload)
shell=shell.replace('<!-- SITE_ANALYTICS -->','<script async src="https://cloud.umami.is/script.js" data-website-id="e01c9f78-4607-4e60-b01c-77c8190b12b4" data-domains="xiaosang.cc"></script>' if settings.cloudflare_static else '')
shell=shell.replace('<!-- SEED_POSTS -->',''.join(seed_html))
shell=shell.replace('<!-- CATALOG_CONFIG -->',config)
shell=shell.replace('<!-- CRITICAL_GRID -->','<script>'+(root/'src/masonry.js').read_text()+'</script>')
(out/'index.html').write_text(shell)
if settings.cloudflare_static:
    for f in ('favicon.svg','vendor/lucide.js','vendor/lucide.LICENSE','skills/index.html','skills/skills.css','skills/skills.js'):
        release_file(f)
    for p in profiles:
        package=Path('skills/packages')/('gallery-'+p['id'])
        release_file(package/'SKILL.md')
        for work in p['works'][:2]:
            release_file(package/'assets'/(work['id']+'.webp'))
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    (out/'release.json').write_text(dump({'project':'xiaosang-gallery','version':version,'commit':head,'series':len(meta),'works':sum(s['works'] for s in meta),'posts':len(feed)})+'\n')
    headers=(root/'src/cloudflare-headers').read_text()
    (out/'_headers').write_text(headers)
    staged=[f for f in out.rglob('*') if f.is_file()]
    if len(staged)>20_000 or any(f.stat().st_size>25*1024**2 for f in staged):
        raise RuntimeError('Release exceeds Workers Static Assets limits')
    print(json.dumps(dict(files=len(staged),bytes=sum(f.stat().st_size for f in staged))))
elif out!=root:
    for name in ['media','originals','vendor','skills','favicon.svg']:
        destination=out/name
        if not destination.exists(): destination.symlink_to(root/name,target_is_directory=(root/name).is_dir())

catalog_facts={'series':counts,'plots':len(meta),'works':sum(s['works'] for s in meta),'posts':len(feed)}
print(json.dumps(catalog_facts,ensure_ascii=False))
