"""Create a standalone *snapshot demo*; scheduled updates only run on hosted source."""
from pathlib import Path
from .core import ROOT

def main():
    html=(ROOT/'index.html').read_text(encoding='utf-8')
    style=(ROOT/'styles.css').read_text(encoding='utf-8')
    data=(ROOT/'data.js').read_text(encoding='utf-8')
    app=(ROOT/'app.js').read_text(encoding='utf-8')
    html=html.replace('<link rel="stylesheet" href="styles.css" />',f'<style>\n{style}\n</style>')
    html=html.replace('<script src="data.js"></script>',f'<script>\n{data}\n</script>')
    html=html.replace('<script src="app.js"></script>',f'<script>\n{app}\n</script>')
    if 'src="data.js"' in html or 'src="app.js"' in html:
        raise AssertionError('Standalone demo still references relative scripts')
    out=ROOT.parent/'RISE_Conference_Navigator_v11_Demo.html'
    out.write_text(html,encoding='utf-8')
    print('Generated standalone (not automatically updated) preview:',out)
if __name__=='__main__':main()
