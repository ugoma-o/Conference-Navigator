"""Conservative unattended publishing of explicit conference and award dates."""
from __future__ import annotations
import argparse
import copy
import datetime as dt
import json
import re
from pathlib import Path
from urllib.parse import urlparse
from .core import ROOT, DATE_RE, MONTHS, OPEN_SUBMIT_BY, LATE_BREAKING_RANGE, _date_for_range, parse_date, validate
from .cli import write_json

FIELDS={'open','deadline','lateOpen','lateDeadline'}
EXCLUDE=re.compile(r'\b(?:workshops?|membership|exhibitor|sponsor|reservation|abstract notification|decisions? released)\b',re.I)
# Registration and hotel terms may share an announcement with an explicit abstract
# event. We still require exactly one date and a matching abstract label below.
LABELS={
 ('conference','open'):r'(?:abstract submissions?|abstract center|call for submissions?)\s+(?:are\s+)?(?:open|opens|opening|begins?|starts?)',
 ('conference','deadline'):r'(?:abstract (?:submission )?deadline|(?:abstract )?submissions?\s+(?:close|closes|closing|due)|deadline to submit abstracts?)',
 ('conference','lateOpen'):r'late[- ]breaking\s+(?:abstract\s+)?(?:submissions?\s+)?(?:opens?|opening|begins?|starts?)',
 ('conference','lateDeadline'):r'late[- ]breaking\s+(?:abstract\s+)?(?:submission\s+)?(?:deadline|closes?|due|ends?)',
 ('award','open'):r'(?:award|grant|scholarship|travel award)?\s*applications?\s+(?:open|opens|begin|begins|start|starts)',
 ('award','deadline'):r'(?:applications?\s+(?:deadline|close|closes|due|end|ends)|application deadline|apply by)'
}

def explicit_window_field(evidence, field):
    """Validate a specific opening/closing date against one labelled pair.

    Multi-date paragraphs must match an established abstract-range grammar;
    arbitrary nearby dates remain disallowed.
    """
    if field in ('open','deadline'):
        matches=list(OPEN_SUBMIT_BY.finditer(evidence))
        if len(matches)!=1:return None
        m=matches[0]
        finish=parse_date(m.group('second'))
        begin=_date_for_range(m.group('first'),int(finish[:4])) if finish else None
        if not begin or begin>finish:return None
        return begin if field=='open' else finish
    if field in ('lateOpen','lateDeadline'):
        matches=list(LATE_BREAKING_RANGE.finditer(evidence))
        if len(matches)!=1:return None
        m=matches[0]
        year=int(m.group('year'))
        begin=_date_for_range(m.group('first'),year)
        first_month=re.search(r'(?i)\b(?:'+'|'.join(MONTHS)+r')\b',m.group('first'))
        month=m.group('lastmonth') or (first_month.group() if first_month else None)
        try:finish=dt.date(year,MONTHS[month.lower()],int(m.group('lastday'))).isoformat()
        except (AttributeError,KeyError,ValueError):return None
        if not begin or begin>finish or (dt.date.fromisoformat(finish)-dt.date.fromisoformat(begin)).days>45:return None
        return begin if field=='lateOpen' else finish
    return None

def same_evidence_date(p):
    evidence=p.get('evidence','')
    pattern=LABELS.get((p.get('record_type'),p.get('field')))
    if not pattern or EXCLUDE.search(evidence):return False
    if p.get('record_type')=='conference' and p.get('field') in ('open','deadline','lateOpen','lateDeadline'):
        if explicit_window_field(evidence,p['field'])==p.get('proposed_value'):
            return True
    dates=list(DATE_RE.finditer(evidence))
    if len(dates)!=1 or parse_date(dates[0].group())!=p.get('proposed_value'):return False
    late=bool(re.search(r'late[- ]breaking',evidence,re.I))
    if p.get('record_type')=='conference' and (p['field'] in ('lateOpen','lateDeadline'))!=late:return False
    labels=list(re.finditer(pattern,evidence,re.I))
    return len(labels)==1 and min(abs(labels[0].end()-dates[0].start()),abs(dates[0].end()-labels[0].start()))<=90

def official_sources_for(record, report, record_type, record_id):
    """Configured official URLs plus successfully fetched same-host links."""
    configured={x for x in (record.get('url'),record.get('guideline'),
                            record.get('submissionSource'),*(record.get('additionalSources') or []))
                if x and urlparse(x).scheme=='https'}
    accepted=set(configured)
    for entry in report.get('discovered_sources',[]):
        if entry.get('record_type')!=record_type or entry.get('record_id')!=record_id:
            continue
        parent=entry.get('parent_url','')
        child=entry.get('source_url','')
        if parent not in configured or not child or not entry.get('link_label'):
            continue
        p1=urlparse(parent);p2=urlparse(child)
        if (p2.scheme=='https' and p2.hostname and p2.hostname==p1.hostname
                and p2.username is None and p2.password is None):
            accepted.add(child)
    return accepted

def resolve_updates(data,report,max_updates=8):
    validate(data)
    if report.get('schema_version')!=2:raise ValueError('Unexpected scan schema: no updates applied')
    index={kind:{r['id']:r for r in data[key]} for kind,key in [('conference','conferences'),('award','awards')]}
    conflicts={(c.get('record_type'),c.get('record_id')) for c in report.get('conflicts',[])}
    accepted=[];held=[]
    for p in report.get('proposals',[]):
        key=(p.get('record_type'),p.get('record_id'))
        record=index.get(key[0],{}).get(key[1])
        reason=''
        field=p.get('field'); val=p.get('proposed_value')
        if record is None:reason='Unknown record'
        elif key in conflicts:reason='Conflicting source evidence'
        elif field not in FIELDS or (key[0]=='award' and field not in ('open','deadline')):reason='Unsupported field'
        elif p.get('review_status')!='requires_human_verification':reason='Unexpected source status'
        elif urlparse(p.get('source_url','')).scheme!='https' or p['source_url'] not in official_sources_for(record,report,key[0],key[1]):reason='Untrusted source URL'
        elif not same_evidence_date(p):reason='Date and event label not clearly paired'
        else:
            try: date=dt.date.fromisoformat(val)
            except (ValueError,TypeError):reason='Invalid date'
            if not reason and key[0]=='conference' and record.get('start'):
                meeting=dt.date.fromisoformat(record['start'])
                if not meeting-dt.timedelta(days=550)<=date<meeting:reason='Date outside meeting cycle'
            old=record.get(field) or (record.get('opens') if key[0]=='award' and field=='open' else None)
            if not reason and old!=p.get('current_value'):reason='Record changed since scan'
            if not reason:
                opening=val if field=='open' else record.get('open') or record.get('opens')
                deadline=val if field=='deadline' else record.get('deadline')
                if opening and deadline and opening>deadline:reason='Invalid open/close order'
                if field=='lateOpen' and record.get('lateDeadline') and val>record['lateDeadline']:reason='Invalid late abstract order'
                if field=='lateDeadline' and record.get('lateOpen') and val<record['lateOpen']:reason='Invalid late abstract order'
            sources=set(p.get('corroborating_sources',[]))
            allowed=official_sources_for(record,report,key[0],key[1])
            if not reason and old and record.get('evidence')!='tracker' and (len(sources & allowed)<2 or p['source_url'] not in sources):reason='Existing official date needs two agreeing configured official URLs'
        if reason:held.append({'id':p.get('id'),'reason':reason})
        else:accepted.append(p)
    if len(accepted)>max_updates:
        return [],held+[{'reason':'Safety circuit breaker: too many date changes'}],True
    return accepted,held,False

def publish_changes(data,report,max_updates=8,checked_at=None):
    updated=copy.deepcopy(data)
    accepted,held,halted=resolve_updates(updated,report,max_updates)
    stamp=checked_at or dt.datetime.now(dt.timezone.utc).isoformat()
    audit=[]
    for p in accepted:
        records=updated['conferences' if p['record_type']=='conference' else 'awards']
        row=next(r for r in records if r['id']==p['record_id'])
        old=row.get(p['field']);row[p['field']]=p['proposed_value']
        configured={x for x in (row.get('url'),row.get('guideline'),
                                 row.get('submissionSource'),*(row.get('additionalSources') or [])) if x}
        if p['source_url'] not in configured:
            # Keep verified discovery targets in the future weekly allowlist.
            row.setdefault('additionalSources',[]).append(p['source_url'])
        if p['record_type']=='award' and p['field']=='open':row['opens']=p['proposed_value']
        row.setdefault('fieldSources',{})[p['field']]={
            'url':p['source_url'],'checked_at':stamp,'verified_by':'RISE conservative auto-publisher',
            'source_quote':p['evidence'],'confidence':'explicit_statement',
            'corroborating_sources':p.get('corroborating_sources',[])}
        audit.append({'id':p['id'],'record_id':p['record_id'],'field':p['field'],
                      'old':old,'new':p['proposed_value'],'source_url':p['source_url']})
    # Publish a new annual edition only when official meeting dates are explicit.
    from .rollover import make_cycle_record,series_year
    existing_ids={c['id'] for c in updated['conferences']}
    existing_series={c['id']:c for c in updated['conferences']}
    additions=[]
    for proposal in report.get('future_candidates',[]):
        prior=existing_series.get(proposal.get('priorCycleId'))
        cid=proposal.get('record_id')
        if not prior or not cid or cid in existing_ids:
            continue
        if series_year(prior) is None or proposal.get('year')<=series_year(prior):
            continue
        if proposal.get('source_url') not in (prior.get('url'),prior.get('guideline'),prior.get('submissionSource')):
            continue
        if len(audit)+len(additions)>=max_updates:
            held.append({'id':cid,'reason':'Weekly new-record safety limit'})
            continue
        record=make_cycle_record(prior,proposal,stamp)
        additions.append(record);existing_ids.add(cid)
        audit.append({'id':cid,'record_id':cid,'field':'new_cycle',
                      'old':None,'new':record['start'],'source_url':proposal['source_url']})
    updated['conferences'].extend(additions)
    if audit:updated['asOf']=stamp[:10]
    validate(updated)
    return updated,{'published':audit,'held':held,'automatic':True,'checked_at':stamp,
                    'circuit_breaker_triggered':halted}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--report',type=Path,default=ROOT/'pipeline/reports/review_queue.json')
    ap.add_argument('--max-updates',type=int,default=8)
    args=ap.parse_args()
    data=json.loads((ROOT/'data.json').read_text(encoding='utf-8'))
    report=json.loads(args.report.read_text(encoding='utf-8'))
    updated,summary=publish_changes(data,report,max_updates=args.max_updates)
    write_json(ROOT/'pipeline/reports/auto_publish_summary.json',summary)
    if summary['published']:
        write_json(ROOT/'data.json',updated)
        import subprocess,sys
        subprocess.run([sys.executable,str(ROOT/'sync_data.py')],cwd=ROOT,check=True)
    print(f"Auto-publishing: {len(summary['published'])} published; {len(summary['held'])} held.")

if __name__=='__main__':main()
