"""Fetch, compare and propose reviewable changes to RISE conference data.

No proposal is published without explicit reviewer approval. Standard-library only.
"""
from __future__ import annotations
import datetime as dt
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parent.parent
MONTHS = {m.lower(): i for i, m in enumerate(['January','February','March','April','May','June','July','August','September','October','November','December'], 1)}
MONTH_PATTERN = '|'.join(MONTHS)
DATE_RE = re.compile(rf'\b(?:(?P<month>{MONTH_PATTERN})\s+(?P<day>\d{{1,2}})(?:st|nd|rd|th)?[,]?\s+(?P<year>20\d{{2}})|(?P<iso>20\d{{2}}-\d{{2}}-\d{{2}}))\b', re.I)
# Keep patterns deliberately narrow: an unlabeled date is not an actionable deadline.
CONFERENCE_LABELS = {
    'open': [r'(?:abstract\s+)?(?:submission\s+portals?|submissions?|abstracts?)\s+(?:are\s+)?(?:open(?:ing)?|begin(?:s)?)(?:\s+on)?', r'abstract\s+submissions?\s+(?:open|start)(?:s)?', r'submission\s+portals?\b.{0,90}?\bopen(?:s|ed)?\b'],
    'deadline': [r'abstract\s+deadline',r'(?:abstract\s+)?submission\s+deadline', r'(?:abstract\s+)?deadline\s+to\s+submit(?:\s+abstracts?)?', r'abstracts?\s+(?:close|due|end)(?:s)?(?:\s+on)?', r'abstract\s+submissions?\s+(?:close|end)(?:s)?(?:\s+on)?'],
    'lateDeadline': [r'late[- ]breaking\s+(?:abstract\s+)?(?:submission\s+)?deadline', r'late[- ]breaking\s+(?:abstracts?\s+)?(?:due|closes?)'],
    'lateOpen': [r'late[- ]breaking\s+(?:abstract\s+)?(?:submissions?\s+)?(?:open(?:s)?|begins?)'],
}
AWARD_LABELS = {
    'open': [r'(?:award|grant|travel\s+award|scholarship)\s+applications?\s+(?:open|begin)(?:s)?', r'applications?\s+(?:open|begin)(?:s)?'],
    'deadline': [r'application\s+deadline', r'applications?\s+(?:close|due|end)(?:s)?', r'apply\s+by'],
}

class VisibleHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript', 'svg', 'template'):
            self.skip += 1
        elif tag in ('p','div','li','h1','h2','h3','h4','tr','br','section','td'):
            self.parts.append(' . ')
    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript', 'svg', 'template'):
            self.skip = max(0, self.skip-1)
        elif tag in ('p','li','h1','h2','h3','h4','tr','td'):
            self.parts.append(' . ')
    def handle_data(self, text):
        if not self.skip:
            self.parts.append(text)

def textify(page: str, is_html=True):
    if is_html:
        parser = VisibleHTML()
        parser.feed(page)
        page = ' '.join(parser.parts)
    return re.sub(r'\s+', ' ', page).strip()

def parse_date(text: str):
    match = DATE_RE.search(text)
    if not match:
        return None
    try:
        if match.group('iso'):
            return dt.date.fromisoformat(match.group('iso')).isoformat()
        return dt.date(int(match.group('year')), MONTHS[match.group('month').lower()], int(match.group('day'))).isoformat()
    except ValueError:
        return None

def extract_labeled_dates(text, kind, year=None):
    """Return only labeled, explicit-year dates with nearby verbatim evidence.

    This is intentionally a candidate generator, not a generic LLM guess.
    """
    labels = AWARD_LABELS if kind == 'award' else CONFERENCE_LABELS
    candidates = []
    for field, patterns in labels.items():
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.I):
                # Short bounded span; do not match across sentence/panel boundaries.
                tail = text[match.end():match.end()+82]
                boundary = re.search(r'\s+\.\s+', tail)
                if boundary:
                    tail = tail[:boundary.start()]
                dm = DATE_RE.search(tail)
                if not dm or dm.start() > 45:
                    continue
                val = parse_date(dm.group())
                if not val:
                    continue
                if year and not (int(year)-1 <= int(val[:4]) <= int(year)):
                    continue
                start = max(0, match.start()-70)
                stop = min(len(text), match.end()+dm.end()+50)
                quote = text[start:stop].strip()
                candidates.append({'field': field, 'value':val, 'evidence':quote})
    # A generic 'deadline to submit' must be on a page discussing abstracts;
    # an unrelated grant/application deadline cannot become a conference deadline.
    if kind == 'conference' and not re.search(r'abstract|scientific\s+submission',text,re.I):
        return []
    unique = {(c['field'], c['value']):c for c in candidates}
    return list(unique.values())

def source_targets(data):
    targets = {}
    for kind, collection in [('conference',data['conferences']),('award',data['awards'])]:
        for item in collection:
            urls = [item.get('url')]
            if kind == 'conference':
                urls += [item.get('guideline'), item.get('submissionSource')]
            for url in urls:
                if url and url.startswith('https://'):
                    targets.setdefault(url, []).append({'kind':kind,'id':item['id'],'name':item['name'],'start':item.get('start')})
    return targets

_robot_cache = {}

def fetch(url, timeout=14, max_bytes=1_500_000):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or not parsed.hostname:
        raise ValueError('Only HTTPS source URLs are supported')
    # Follow robots.txt where available; a blocked page is reported, never bypassed.
    origin=f'{parsed.scheme}://{parsed.netloc}'
    if origin not in _robot_cache:
        robots=RobotFileParser(origin+'/robots.txt')
        try:
            robots_req=Request(origin+'/robots.txt',headers={'User-Agent':'RISE-Conference-Navigator/1.0'})
            with urlopen(robots_req,timeout=min(timeout,6)) as response:
                rules=response.read(150_001)
                if len(rules)>150_000: raise ValueError('robots.txt too large')
                robots.parse(rules.decode('utf-8',errors='replace').splitlines())
                _robot_cache[origin]=robots
        except HTTPError as error:
            if error.code in (401,403):
                raise ValueError('robots.txt access restricted') from error
            _robot_cache[origin]=None
        except (URLError, TimeoutError, OSError):
            raise ValueError('Unable to establish robots.txt access policy')
    rule=_robot_cache[origin]
    if rule is not None and not rule.can_fetch('RISE-Conference-Navigator',url):
        raise ValueError('Disallowed by robots.txt')
    req=Request(url,headers={'User-Agent':'RISE-Conference-Navigator/1.0 (academic conference metadata; 1 request per source)', 'Accept':'text/html, text/plain;q=0.8'})
    with urlopen(req,timeout=timeout) as r:
        content_type=r.headers.get('Content-Type','').lower()
        if not any(x in content_type for x in ('text/html','text/plain')):
            raise ValueError('Unsupported response type: '+content_type)
        payload = r.read(max_bytes+1)
        if len(payload)>max_bytes:
            raise ValueError('Source exceeds maximum download size')
        return payload.decode('utf-8',errors='replace'), 'text/html' in content_type

def short_id(kind, record_id, field, value, url):
    return hashlib.sha256(f'{kind}|{record_id}|{field}|{value}|{url}'.encode()).hexdigest()[:16]

def check_sources(data, cache=None, fetcher=fetch, limit=None, delay=0, timeout=14, checked_at=None):
    """Return report and persistent cache; replace fetcher in deterministic tests."""
    cache = cache or {}
    checked_at = checked_at or dt.datetime.now(dt.timezone.utc).isoformat()
    targets = list(source_targets(data).items())
    if limit is not None:
        targets=targets[:limit]
    output=[]; proposals=[]; updated=dict(cache)
    by_kind = {
        'conference':{c['id']:c for c in data['conferences']},
        'award':{a['id']:a for a in data['awards']},
    }
    for i,(url,records) in enumerate(targets):
        if i and delay: time.sleep(delay)
        prior=cache.get(url,{})
        try:
            page,is_html=fetcher(url,timeout=timeout)
            content = textify(page,is_html)
            if len(content)<70:
                raise ValueError('Source text too short for reliable monitoring')
            digest=hashlib.sha256(content.encode()).hexdigest()
            state='baseline' if not prior.get('digest') else 'changed' if prior['digest']!=digest else 'unchanged'
            for ref in records:
                record=by_kind[ref['kind']][ref['id']]
                year= int(ref['start'][:4]) if ref.get('start') else next((int(y) for y in re.findall(r'20\d{2}',ref['name'])),None)
                if ref['kind']=='award' and record.get('conferenceId'):
                    linked=by_kind['conference'].get(record['conferenceId'])
                    if linked and linked.get('start'): year=int(linked['start'][:4])
                extracted=extract_labeled_dates(content, ref['kind'], year)
                grouped={}
                for hit in extracted:
                    grouped.setdefault(hit['field'],[]).append(hit)
                for field,hits in grouped.items():
                    values={x['value'] for x in hits}
                    if len(values)!=1:
                        # Conflicting dates on one source are not actionable proposals.
                        continue
                    hit=hits[0]; old=record.get(field) or (record.get('opens') if ref['kind']=='award' and field=='open' else None)
                    if old==hit['value']:
                        continue
                    proposal={
                        'id':short_id(ref['kind'],ref['id'],field,hit['value'],url),
                        'record_type':ref['kind'],'record_id':ref['id'],'record_name':ref['name'],
                        'field':field,'current_value':old,'proposed_value':hit['value'],
                        'source_url':url,'evidence':hit['evidence'],
                        'review_status':'requires_human_verification',
                        'reason':'Missing published date' if not old else 'Source date differs from current record',
                    }
                    proposals.append(proposal)
            updated[url]={'digest':digest,'checked_at':checked_at,'length':len(content)}
            output.append({'url':url,'status':state,'records':records,'checked_at':checked_at, 'proposed_count':sum(p['source_url']==url for p in proposals)})
        except (HTTPError,URLError,TimeoutError,ValueError,OSError,UnicodeError) as error:
            output.append({'url':url,'status':'unavailable','records':records,'checked_at':checked_at,'error':str(error)[:300],'proposed_count':0})
    proposals.sort(key=lambda x:(x['record_type'],x['record_id'],x['field'],x['proposed_value']))
    return ({'checked_at':checked_at,'source_count':len(output),'counts':{k:sum(x['status']==k for x in output) for k in ('baseline','changed','unchanged','unavailable')},'checks':output,'proposals':proposals,'publication':'No records changed. Reviewer approval required.'},updated)

def draft_cycle(data, target_year):
    """Produce an unpublished draft; NEVER carry dates or old validation forward."""
    known={(re.sub(r'\b20\d{2}\b','',x['name']).strip(),str(x.get('start',''))[:4]) for x in data['conferences']}
    drafts=[]
    for entry in data['conferences']:
        year=int(entry['start'][:4]) if entry.get('start') else next((int(y) for y in re.findall(r'20\d{2}',entry['name'])),None)
        if year != target_year-1 or (re.sub(r'\b20\d{2}\b','',entry['name']).strip(),str(target_year)) in known:
            continue
        future={**entry}
        old_id=entry['id'];future['id']=re.sub(r'\d{2}$',str(target_year)[-2:],old_id) if re.search(r'\d{2}$',old_id) else f'{old_id}-{target_year}'
        future['name']=re.sub(r'\b'+str(year)+r'\b',str(target_year),entry['name'])
        for field in ('open','deadline','lateOpen','lateDeadline','start','end','deadlineTime'):
            future[field]=None
        for field in ('fee','limit','limitType','limitNote','flag','presentationFormats','presentationPolicy','submissionCategoriesVerified'):
            future[field]=[] if field=='presentationFormats' else False if field=='submissionCategoriesVerified' else None
        future['types']=[]
        future['evidence']='unannounced'
        future['note']='UNPUBLISHED DRAFT: Upcoming cycle not verified. Dates, eligibility, and category rules intentionally blank.'
        future['priorCycleId']=old_id
        drafts.append(future)
    return drafts

def validate(data):
    assert isinstance(data,dict) and isinstance(data.get('conferences'),list) and isinstance(data.get('awards'),list)
    for key in ('conferences','awards'):
        seen=set()
        for item in data[key]:
            assert item.get('id') and item['id'] not in seen, f'Duplicate or empty ID: {item.get("id")}'
            seen.add(item['id'])
            for field in ('start','end','open','deadline','lateOpen','lateDeadline'):
                v=item.get(field)
                if v: dt.date.fromisoformat(v)
    return True

def approve(data, report, candidate_id, reviewer, timestamp=None):
    if not reviewer or len(reviewer.strip())<2:
        raise ValueError('Reviewer name is required')
    hits=[p for p in report.get('proposals',[]) if p['id']==candidate_id]
    if len(hits)!=1:
        raise ValueError('Proposal ID not found or not unique')
    p=hits[0]
    collection='conferences' if p['record_type']=='conference' else 'awards'
    hit=next((x for x in data[collection] if x['id']==p['record_id']),None)
    if not hit:
        raise ValueError('Record no longer exists')
    field=p['field']
    old=hit.get(field) or (hit.get('opens') if collection=='awards' and field=='open' else None)
    if old!=p['current_value']:
        raise ValueError('Record has changed since proposal; review again')
    if not p['source_url'].startswith('https://') or not parse_date(p['proposed_value']):
        raise ValueError('Invalid source or date')
    # Ensure an application/abstract opening cannot be after an existing closing date, etc.
    new=p['proposed_value']
    if field=='open' and hit.get('deadline') and new>hit['deadline']:
        raise ValueError('Opening cannot be after deadline')
    if field=='deadline' and hit.get('open') and new<hit['open']:
        raise ValueError('Deadline cannot be before opening')
    if collection=='conferences' and field=='deadline' and hit.get('start') and new>hit['start']:
        raise ValueError('Abstract deadline cannot be after conference begins')
    hit[field]=new
    if collection=='awards' and field=='open':
        hit['opens']=new  # Keep legacy alias in sync.
    stamp=timestamp or dt.datetime.now(dt.timezone.utc).isoformat()
    hit.setdefault('fieldSources',{})[field]={'url':p['source_url'],'checked_at':stamp,'reviewed_by':reviewer,'source_quote':p['evidence']}
    data['asOf']=stamp[:10]
    validate(data)
    return {'proposal_id':candidate_id,'record_id':hit['id'],'field':field,'old':old,'new':new,'reviewer':reviewer,'at':stamp,'source_url':p['source_url']}
