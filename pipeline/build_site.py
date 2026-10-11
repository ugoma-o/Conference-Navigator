"""Build an allowlisted static app for deployment (no monitor/cache data exposed)."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
from .core import ROOT,validate

def build(out=None):
    out=Path(out or ROOT/'dist')
    data=json.loads((ROOT/'data.json').read_text(encoding='utf-8'))
    validate(data)
    subprocess.run([sys.executable,str(ROOT/'sync_data.py')],check=True,cwd=ROOT)
    out.mkdir(parents=True,exist_ok=True)
    for f in ('index.html','app.js','data.js','data.json','styles.css'):
        shutil.copy2(ROOT/f,out/f)
    # Fingerprint deployed assets to prevent a stale browser UI after updates.
    html=(out/'index.html').read_text(encoding='utf-8')
    for asset,attr in [('styles.css','href'),('data.js','src'),('app.js','src')]:
        version=hashlib.sha256((out/asset).read_bytes()).hexdigest()[:12]
        old_ref=f'{attr}="{asset}"'
        if old_ref not in html:
            raise ValueError(f'Missing expected site asset reference: {old_ref}')
        html=html.replace(old_ref,f'{attr}="{asset}?v={version}"')
    (out/'index.html').write_text(html,encoding='utf-8')
    (out/'.nojekyll').write_text('',encoding='utf-8')
    print(f'Built static site at {out} — {len(data["conferences"])} conferences, {len(data["awards"])} awards')
if __name__=='__main__':build()
