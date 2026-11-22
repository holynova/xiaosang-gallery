"""Build the gallery using an immutable Pages archive and repository additions."""
from hashlib import sha256
from pathlib import Path
import shutil
import json

ROOT = Path(__file__).resolve().parents[1]
MEDIA_ORIGIN = 'https://gallery-media.xiaosang.cc'


def add_photo(path, series, folder):
    from PIL import Image, ImageOps
    digest = sha256(path.read_bytes()).hexdigest()
    ident = 'upload-' + series + '-' + digest[:20]
    original = 'added/originals/' + ident + path.suffix.lower()
    (folder/'added/originals').mkdir(parents=True, exist_ok=True)
    (folder/'added/media/v2').mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, folder/original)
    variants = {}
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image).convert('RGB')
        width, height = image.size
        for size, bound in [('s',384),('detail',1440)]:
            scaled = image.copy()
            scaled.thumbnail((bound,bound), Image.Resampling.LANCZOS)
            paths = []
            for fmt in ['avif','webp']:
                target = f'added/media/v2/{ident}-{size}.{fmt}'
                scaled.save(folder/target, quality=80)
                paths.append(target)
            variants[size] = [*paths,*scaled.size]
    variants['m'] = variants['s']
    return dict(id=ident, title=path.stem, category='', post='', quality='original', alt=path.stem,
                width=width, height=height, crop=[0,0,width,height], variants=variants,
                original=original, sha256=digest)


def catalog(output):
    order = json.loads((ROOT/'catalog/order.json').read_text())
    profiles = [json.loads((ROOT/'catalog'/f'{ident}.json').read_text()) for ident in order]
    groups = {p['id']: p for p in profiles}
    for series in profiles:
        for work in series['works']:
            work['original'] = f"{MEDIA_ORIGIN}/{work['original']}"
            for variant in work['variants'].values():
                variant[:2] = [f"{MEDIA_ORIGIN}/{key}" for key in variant[:2]]
    for path in sorted((ROOT/'additions').glob('*/*')):
        if not path.is_file():
            continue
        series = path.parent.name
        if series not in groups or path.suffix.lower() not in {'.jpg','.jpeg','.png','.webp'}:
            raise ValueError(f'Unsupported series or image: {path.relative_to(ROOT)}')
        work = add_photo(path, series, output)
        if any(item['id'] == work['id'] for item in groups[series]['works']):
            raise ValueError(f'Duplicate image in {series}: {path.name}')
        groups[series]['works'].append(work)
    return profiles
