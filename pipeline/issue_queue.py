"""Create/update one GitHub issue pointing to current evidence artifact.

Requires GH_TOKEN, REPOSITORY and MONITOR_RUN from scheduled GitHub Action.
No personal data or secrets included; source snippets stay in workflow artifact.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parent.parent
TITLE='RISE official-source update review queue'

def main():
    report=json.loads((ROOT/'pipeline/reports/review_queue.json').read_text())
    candidates=report['proposals']
    changed=[c for c in report['checks'] if c['status']=='changed']
    unavailable=[c for c in report['checks'] if c['status']=='unavailable']
    url=f'https://github.com/{os.environ["REPOSITORY"]}/actions/runs/{os.environ["MONITOR_RUN"]}'
    body=(f'RISE source check: **{report["checked_at"]}**\n\n'
          f'- {len(candidates)} proposed date updates requiring independent verification\n'
          f'- {len(changed)} pages changed since last fingerprint\n'
          f'- {len(unavailable)} pages unavailable or unsupported\n\n'
          f'**[View monitoring run and download the review artifact]({url})**\n\n'
          'Open `review_queue.html` to inspect the evidence, then independently confirm the official webpage. '
          'Use Actions → Review and propose a dated change with the monitor run ID and candidate ID. '
          '**No changes publish until the resulting pull request is merged.**\n')
    existing=subprocess.run(['gh','issue','list','--state','open','--limit','100','--json','number,title'],capture_output=True,text=True,check=True)
    issue=next((x for x in json.loads(existing.stdout) if x['title']==TITLE),None)
    if not candidates and not changed and not unavailable:
        if issue: subprocess.run(['gh','issue','close',str(issue['number']),'--comment','Latest scan found no actionable changes.'],check=True)
        print('No review issue necessary')
        return
    if issue:
        subprocess.run(['gh','issue','edit',str(issue['number']),'--body',body],check=True)
        print('Updated issue '+str(issue['number']))
    else:
        subprocess.run(['gh','issue','create','--title',TITLE,'--body',body],check=True)
        print('Created single review issue')
if __name__=='__main__':main()
