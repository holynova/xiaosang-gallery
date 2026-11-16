"""Build a fresh deployment and leave the last build intact if staging fails."""
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
import sys

root = Path(__file__).resolve().parent.parent
with TemporaryDirectory(prefix='.release-', dir=root) as folder:
    stage=Path(folder)/'next'
    subprocess.run([sys.executable, str(root/'scripts/build_site.py'), '--cloudflare-static', '--output', str(stage)], check=True)
    dist=root/'dist'
    previous=Path(folder)/'previous'
    if dist.exists():
        dist.rename(previous)
    try:
        stage.rename(dist)
    except OSError:
        if previous.exists():
            previous.rename(dist)
        raise
