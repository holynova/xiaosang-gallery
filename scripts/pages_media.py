"""Prepare gallery entries for Cloudflare Pages and immutable media in R2."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import argparse
import json
import mimetypes
import os
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
MEDIA_ORIGIN = 'https://gallery-media.xiaosang.cc'
BUCKET = 'xiaosang-gallery-media'
RECEIPT = 'migration/legacy-v1.json'


def upload_tree(folder):
    import boto3
    from botocore.exceptions import ClientError
    client = boto3.client('s3', endpoint_url=os.environ['R2_ENDPOINT'], region_name='auto',
                          aws_access_key_id=os.environ['R2_ACCESS_KEY_ID'],
                          aws_secret_access_key=os.environ['R2_SECRET_ACCESS_KEY'])

    def upload(path):
        key = path.relative_to(folder).as_posix()
        digest = sha256(path.read_bytes()).hexdigest()
        try:
            obj = client.head_object(Bucket=BUCKET, Key=key)
        except ClientError as error:
            if error.response['ResponseMetadata']['HTTPStatusCode'] != 404:
                raise
        else:
            if obj['Metadata'].get('sha256') == digest:
                return
            raise ValueError(f'Existing object differs: {key}')
        options = {'ContentType': mimetypes.guess_type(key)[0] or 'application/octet-stream',
                   'CacheControl': 'public, max-age=31536000, immutable',
                   'Metadata': {'sha256': digest}, 'IfNoneMatch': '*'}
        if key.startswith('originals/'):
            options['ContentDisposition'] = 'attachment'
        with path.open('rb') as body:
            try:
                client.put_object(Bucket=BUCKET, Key=key, Body=body, **options)
            except ClientError as error:
                if error.response['ResponseMetadata']['HTTPStatusCode'] != 412:
                    raise
                if client.head_object(Bucket=BUCKET, Key=key)['Metadata'].get('sha256') != digest:
                    raise
    paths = [f for sub in ('media','originals') for f in (folder/sub).rglob('*') if f.is_file()]
    with ThreadPoolExecutor(max_workers=8) as pool:
        for _ in pool.map(upload, paths):
            pass
    return client, len(paths)


def add_photo(path, series, folder):
    from PIL import Image, ImageOps
    digest = sha256(path.read_bytes()).hexdigest()
    ident = series + '-' + digest[:20]
    original = 'originals/' + ident + path.suffix.lower()
    (folder/'originals').mkdir(exist_ok=True)
    (folder/'media/v2').mkdir(parents=True, exist_ok=True)
    (folder/original).hardlink_to(path)
    variants = {}
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image).convert('RGB')
        width, height = image.size
        for size, bound in [('s',384),('detail',1440)]:
            scaled = image.copy()
            scaled.thumbnail((bound,bound), Image.Resampling.LANCZOS)
            paths = []
            for fmt in ['avif','webp']:
                target = f'media/v2/{ident}-{size}.{fmt}'
                scaled.save(folder/target, quality=80)
                paths.append(target)
            variants[size] = [*paths,*scaled.size]
    variants['m'] = variants['s']
    return dict(id=ident, title=path.stem, category='', post='', quality='original', alt=path.stem,
                width=width, height=height, crop=[0,0,width,height], variants=variants,
                original=original, sha256=digest)


def catalog():
    order = json.loads((ROOT/'catalog/order.json').read_text())
    profiles = [json.loads((ROOT/'catalog'/f'{ident}.json').read_text()) for ident in order]
    if os.environ.get('CF_PAGES_BRANCH') == 'main':
        expected_receipt = json.loads((ROOT/'catalog/legacy-media.json').read_text())
        with urlopen(f'{MEDIA_ORIGIN}/{RECEIPT}', timeout=30) as response:
            if json.load(response) != expected_receipt:
                raise ValueError('R2 baseline receipt does not match this gallery.')
    files = sorted(f for f in (ROOT/'additions').glob('*/*') if f.is_file())
    groups = {p['id']: p for p in profiles}
    with TemporaryDirectory(dir=ROOT) as temp:
        folder = Path(temp)
        for path in files:
            series = path.parent.name
            if series not in groups or path.suffix.lower() not in {'.jpg','.jpeg','.png','.webp'}:
                raise ValueError(f'Unsupported series or image: {path.relative_to(ROOT)}')
            work = add_photo(path, series, folder)
            groups[series]['works'].append(work)
        if files and os.environ.get('CF_PAGES_BRANCH') == 'main':
            upload_tree(folder)
    for series in profiles:
        for work in series['works']:
            work['original'] = MEDIA_ORIGIN + '/' + work['original']
            for variant in work['variants'].values():
                variant[:2] = [MEDIA_ORIGIN + '/' + key.removeprefix(MEDIA_ORIGIN + '/') for key in variant[:2]]
    return profiles


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Copy the existing production media to R2 once.')
    parser.add_argument('dist', type=Path)
    args = parser.parse_args()
    profiles = [json.loads(f.read_text()) for f in (ROOT/'catalog').glob('*.json') if f.stem in json.loads((ROOT/'catalog/order.json').read_text())]
    expected = {key for p in profiles for w in p['works']
                for key in [w['original'], *(v for variant in w['variants'].values() for v in variant[:2])]}
    if not expected or any(not (args.dist/key).is_file() for key in expected):
        raise ValueError('The legacy directory is missing catalog media.')
    client, count = upload_tree(args.dist)
    receipt = {'objects':len(expected),'keysSha256':sha256('\n'.join(sorted(expected)).encode()).hexdigest()}
    client.put_object(Bucket=BUCKET, Key=RECEIPT, Body=json.dumps(receipt).encode(),ContentType='application/json')
    print(f'Verified {count} stored objects and wrote {RECEIPT}.')
