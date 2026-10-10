"""Build an allowlisted static app for deployment (no monitor/cache data exposed)."""
from pathlib import Path
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
    (out/'.nojekyll').write_text('',encoding='utf-8')
    print(f'Built static site at {out} — {len(data["conferences"])} conferences, {len(data["awards"])} awards')
if __name__=='__main__':build()
