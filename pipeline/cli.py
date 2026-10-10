"""RISE monitor/review CLI. Example: python -m pipeline.cli scan --limit 10."""
from __future__ import annotations
import argparse
import datetime as dt
import html
import json
from pathlib import Path
import sys
from .core import ROOT, check_sources, draft_cycle, approve, validate

DEFAULT_REPORT=ROOT/'pipeline'/'reports'/'review_queue.json'
DEFAULT_CACHE=ROOT/'pipeline'/'.source_cache.json'

def read_json(p, default=None):
    return json.loads(Path(p).read_text(encoding='utf-8')) if Path(p).exists() else default

def write_json(p, value):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def report_html(report, path):
    """Human-readable, inert report; all page text is escaped."""
    escape=html.escape
    head='''<!doctype html><html lang="en"><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RISE source review</title><style>body{max-width:1000px;margin:2rem auto;padding:1rem;font:16px/1.55 system-ui;color:#193c40;background:#f5f8f7}article{background:white;border:1px solid #d9e6e1;border-radius:12px;padding:1rem;margin:1rem 0}small,code{color:#59706b}code{overflow-wrap:anywhere}h1{font-size:1.8rem}h2{font-size:1.12rem}blockquote{margin:1rem 0;padding:.7rem 1rem;border-left:4px solid #6c9a84;background:#edf4f1}a{color:#155d6b}</style>'''
    body=f'<h1>RISE Source Review Queue</h1><p>Checked: {escape(report["checked_at"])} · Sources: {report["source_count"]} · Proposed changes: {len(report["proposals"])}</p><p><b>Nothing in this report has been published.</b> Check the official webpage before approving any proposal.</p>'
    for p in report['proposals']:
        link=escape(p['source_url'],quote=True)
        body+=f'<article><h2>{escape(p["record_name"])} — {escape(p["field"])}</h2><p>Current: <b>{escape(str(p["current_value"]))}</b> → Proposed: <b>{escape(p["proposed_value"])}</b></p><p>Review ID: <code>{escape(p["id"])}</code></p><blockquote>{escape(p["evidence"])}</blockquote><p><a href="{link}" rel="noopener noreferrer" target="_blank">Official source ↗</a></p></article>'
    bad=[x for x in report['checks'] if x['status']=='unavailable']
    body+=f'<h2>Sources unavailable ({len(bad)})</h2>'
    for x in bad:
        body+=f'<p><code>{escape(x["url"])}</code>: {escape(x.get("error",""))}</p>'
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(head+'<body>'+body+'</body></html>',encoding='utf-8')

def main():
    ap=argparse.ArgumentParser(description='RISE conference updates: review-required pipeline')
    sub=ap.add_subparsers(dest='cmd',required=True)
    scan=sub.add_parser('scan',help='Fetch official pages and create review candidates, never edit records')
    scan.add_argument('--all',action='store_true')
    scan.add_argument('--limit',type=int,default=20)
    scan.add_argument('--delay',type=float,default=1.0)
    scan.add_argument('--timeout',type=float,default=14.0)
    scan.add_argument('--cache',type=Path,default=DEFAULT_CACHE)
    scan.add_argument('--report',type=Path,default=DEFAULT_REPORT)
    review=sub.add_parser('approve',help='Apply one human-reviewed source proposal to data.json')
    review.add_argument('--candidate',required=True)
    review.add_argument('--reviewer',required=True)
    review.add_argument('--report',type=Path,default=DEFAULT_REPORT)
    review.add_argument('--apply',action='store_true',help='Required to write changes')
    cycle=sub.add_parser('draft-cycle',help='Generate UNPUBLISHED next-year placeholders')
    cycle.add_argument('--year',type=int,required=True)
    cycle.add_argument('--out',type=Path,default=ROOT/'pipeline'/'reports'/'future_cycle_draft.json')
    v=sub.add_parser('validate',help='Validate data records and regenerate browser-readable data.js')
    args=ap.parse_args()
    data_path=ROOT/'data.json'
    data=read_json(data_path)
    validate(data)
    if args.cmd=='scan':
        previous=read_json(args.cache,{})
        report,new_cache=check_sources(data,previous,limit=None if args.all else args.limit,delay=args.delay,timeout=args.timeout)
        write_json(args.cache,new_cache)
        write_json(args.report,report)
        report_html(report,args.report.with_suffix('.html'))
        print(f'Checked {report["source_count"]} sources; {len(report["proposals"])} review proposals, {report["counts"]["unavailable"]} unavailable.')
        print(f'Review {args.report} and {args.report.with_suffix(".html")}. No data changed.')
    elif args.cmd=='approve':
        report=read_json(args.report)
        if not report:
            ap.error('Report missing; run scan first or provide --report')
        # Work on a copy so validation failures cannot partially modify persisted data.
        result=approve(data,report,args.candidate,args.reviewer)
        if not args.apply:
            print('DRY RUN ONLY (pass --apply to update): '+json.dumps(result))
            return
        write_json(data_path,data)
        audit=ROOT/'pipeline'/'approved_changes.jsonl'
        with audit.open('a',encoding='utf-8') as f:f.write(json.dumps(result,ensure_ascii=False)+'\n')
        from subprocess import run
        run([sys.executable,str(ROOT/'sync_data.py')],cwd=ROOT,check=True)
        print('APPROVED and synced: '+json.dumps(result))
    elif args.cmd=='draft-cycle':
        candidates=draft_cycle(data,args.year)
        write_json(args.out,{'year':args.year,'status':'unpublished_drafts_needing_source_review','conferences':candidates})
        print(f'{len(candidates)} unpublished {args.year} drafts prepared: {args.out}. No public data changed.')
    else:
        from subprocess import run
        run([sys.executable,str(ROOT/'sync_data.py')],check=True,cwd=ROOT)
        print('Validated and synchronized.')

if __name__=='__main__': main()
