"""Fetch official sources and propose date changes with supporting evidence.

Extraction itself does not publish. The independent auto_publish module enforces
a conservative, unattended publication policy. Standard-library only.
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
    if not is_html:
        page=re.sub(r'(?:\r?\n)+', ' . ', page)
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

# Each candidate must be attached to its own dated clause. Never attach the
# closing date of an opening-to-closing range to the word "open".
SHORT_DATE = rf'(?:{MONTH_PATTERN})\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+20\d{{2}})?'
OPEN_CLOSE_RANGE = re.compile(
    rf'\b(?:abstract\s+)?submissions?\s+(?:are\s+)?open\s+from\s+'
    rf'(?P<first>{SHORT_DATE})\s+(?:through|to|until|[-–])\s+'
    rf'(?P<second>{SHORT_DATE})', re.I)
OPEN_AND_CLOSE = re.compile(
    rf'\b(?:abstract\s+)?submissions?\s+open\s+'
    rf'(?P<first>{SHORT_DATE})\s+and\s+close\s+'
    rf'(?P<second>{SHORT_DATE})', re.I)
# Some official pages describe the abstract submission window as "opens DATE
# and must be submitted by TIME on DATE" rather than labeling the close as
# a "deadline." Require the entire linked statement before extracting either.
OPEN_SUBMIT_BY = re.compile(
    rf'\b(?:abstract\s+)?submissions?\s+open\s+(?P<first>{SHORT_DATE})\s*,?\s+'
    rf'and\s+must\s+be\s+submitted\s+by\b.{{0,90}}?\b(?P<second>{SHORT_DATE})',re.I)
# SID-style short ranges explicitly name late-breaking abstracts but express
# the closing day as just a number: "March 1 – 18, 2027".
LATE_BREAKING_RANGE = re.compile(
    rf'\blate[- ]breaking\s+abstracts?\s+can\s+be\s+submitted\s+'
    rf'(?P<first>{SHORT_DATE})\s*(?:-|–|—|to|through)\s*'
    rf'(?:(?P<lastmonth>{MONTH_PATTERN})\s+)?'
    rf'(?P<lastday>\d{{1,2}})(?:st|nd|rd|th)?,?\s+(?P<year>20\d{{2}})\b',re.I)

AWARD_RANGE = re.compile(
    rf'\b(?:award|grant|scholarship)\s+applications?\s+(?:are\s+)?open\s+from\s+'
    rf'(?P<first>{SHORT_DATE})\s+(?:through|to|until|[-–])\s+'
    rf'(?P<second>{SHORT_DATE})', re.I)

# Extra labels exist in real source pages, including the AANS abstract center.
CONFERENCE_LABELS['open'].extend([
    r'abstract\s+center\s+opens?',
    r'call\s+for\s+submissions?\s+open',
])
CONFERENCE_LABELS['deadline'].extend([
    r'abstract\s+center\s+closes?',
    r'abstract\s+center\s+extension',
    r'call\s+for\s+submissions?\s+clos(?:e|es)',
])

def _parts(text):
    # ' . ' is the separator inserted for block-level HTML elements by textify.
    return [part.strip().strip(' .') for part in re.split(r'\s+\.\s+', text) if part.strip().strip(' .')]

def _date_for_range(part, year_hint=None):
    """Resolve an explicitly written date, or a yearless date only within a
    clearly linked OPEN/CLOSE range where the second date supplies the year."""
    val=parse_date(part)
    if val:
        return val
    if year_hint is None:
        return None
    m=re.search(rf'(?P<month>{MONTH_PATTERN})\s+(?P<day>\d{{1,2}})',part,re.I)
    if not m:
        return None
    try:
        return dt.date(year_hint,MONTHS[m.group('month').lower()],int(m.group('day'))).isoformat()
    except ValueError:
        return None

def _year_plausible(value, conference_year):
    return not conference_year or conference_year-1 <= int(value[:4]) <= conference_year

def _cycle_matches_page(text, kind, conference_year, record_name=None):
    """Conservative meeting-year gate. Do not recycle a 2026-only abstract
    page as proof of deadlines for a 2027 meeting. Missing context -> no proposal.
    Awards can be standalone and may not mention a meeting year."""
    if kind != 'conference' or not conference_year:
        return True
    if not re.search(rf'\b{conference_year}\b',text):
        return False
    # Some sites place a generic future-year promotion in navigation while
    # the actual abstract call is explicitly for an older year (ACG 2026 on
    # a page with unrelated 2027 navigation, for example). Detect strong
    # society-acronym-plus-year context and do not let the navigation year
    # override an explicit old-cycle identity.
    acronym=re.match(r'([A-Z][A-Z0-9&-]{1,9})\b',record_name or '')
    if acronym:
        abbr=re.escape(acronym.group(1))
        named=set()
        for m in re.finditer(rf'\b{abbr}[\s:.-]+(20\d{{2}})\b|\b(20\d{{2}})[\s:.-]+{abbr}\b',text,re.I):
            named.add(int(m.group(1) or m.group(2)))
        if named and conference_year not in named:
            return False
    return True

def extract_labeled_dates(text, kind, year=None, record_name=None):
    """Extract candidates only when source language explicitly binds a date to
    the correct submission event. Conflicts are evaluated by check_sources.

    Important: this is a conservative candidate generator, not verification.
    """
    if not _cycle_matches_page(text,kind,year,record_name):
        return []
    labels=AWARD_LABELS if kind=='award' else CONFERENCE_LABELS
    parts=_parts(text)
    found=[]
    for i,clause in enumerate(parts):
        # Range statements require special treatment. The second date must
        # explicitly supply the year; only then may the first inherit it.
        ranges=[AWARD_RANGE] if kind=='award' else [OPEN_CLOSE_RANGE,OPEN_AND_CLOSE]
        matched_range=False
        for rx in ranges:
            for match in rx.finditer(clause):
                finish=parse_date(match.group('second'))
                if not finish: continue
                begin=_date_for_range(match.group('first'),int(finish[:4]))
                if not begin or begin>finish or (dt.date.fromisoformat(finish)-dt.date.fromisoformat(begin)).days>365:
                    continue
                for field,val in [('open',begin),('deadline',finish)]:
                    if _year_plausible(val,year):
                        found.append({'field':field,'value':val,'evidence':clause[:400]})
                        matched_range=True
        if kind=='conference':
            for match in OPEN_SUBMIT_BY.finditer(clause):
                finish=parse_date(match.group('second'))
                begin=_date_for_range(match.group('first'),int(finish[:4])) if finish else None
                if not begin or begin>finish or (dt.date.fromisoformat(finish)-dt.date.fromisoformat(begin)).days>365:
                    continue
                for field,val in [('open',begin),('deadline',finish)]:
                    if _year_plausible(val,year):
                        found.append({'field':field,'value':val,'evidence':clause[:400]})
                        matched_range=True
            for match in LATE_BREAKING_RANGE.finditer(clause):
                finish_year=int(match.group('year'))
                begin=_date_for_range(match.group('first'),finish_year)
                first_month=re.search(rf'(?P<month>{MONTH_PATTERN})',match.group('first'),re.I)
                last_month=match.group('lastmonth') or (first_month.group('month') if first_month else None)
                try:
                    finish=dt.date(finish_year,MONTHS[last_month.lower()],int(match.group('lastday'))).isoformat()
                except (AttributeError,KeyError,ValueError):
                    continue
                if not begin or begin>finish or (dt.date.fromisoformat(finish)-dt.date.fromisoformat(begin)).days>45:
                    continue
                for field,val in [('lateOpen',begin),('lateDeadline',finish)]:
                    if _year_plausible(val,year):
                        found.append({'field':field,'value':val,'evidence':clause[:400]})
                        matched_range=True
        if matched_range:
            # Do not assign another field's date from a combined submission
            # window to a generic label in the same paragraph.
            continue
        for field,patterns in labels.items():
            for pattern in patterns:
                for label in re.finditer(pattern,clause,re.I):
                    # Late-breaking terms should never become regular dates.
                    vicinity=clause[max(0,label.start()-32):min(len(clause),label.end()+18)]
                    if kind=='conference' and field in ('open','deadline') and re.search(r'late[- ]breaking',vicinity,re.I):
                        continue
                    # A fragment "open DATE and close DATE" must only be
                    # parsed via a coherent range above; otherwise abstain.
                    if field=='open' and re.search(r'\b(?:and\s+close|through|until|\bto\b)\b',clause[label.end():label.end()+110],re.I):
                        continue
                    tail=clause[label.end():label.end()+85]
                    # Do not jump over unrelated labeled fields to find a date.
                    next_label=re.search(r'\b(?:open|opens|close|closes|deadline|due|begin|begins)\b',tail,re.I)
                    dm=DATE_RE.search(tail)
                    if not dm and len(clause)<85 and label.end()>=len(clause)-25 and i+1<len(parts):
                        # A heading like "Abstract Center Closes" followed by
                        # "Thursday, October 1, 2026" is valid. Require that
                        # the following block STARTS with a date/day-of-week.
                        after=parts[i+1]
                        if re.match(r'^(?:(?:Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day,?\s+)?(?:'+MONTH_PATTERN+r')\s+\d{1,2}',after,re.I):
                            tail=after[:65];dm=DATE_RE.search(tail);next_label=None
                    if not dm or dm.start()>65:
                        continue
                    if next_label and next_label.start()<dm.start():
                        continue
                    val=parse_date(dm.group())
                    if val and _year_plausible(val,year):
                        found.append({'field':field,'value':val,'evidence':clause[:400] if dm.group() in clause else (clause+' / '+tail)[:400]})
    # Pages that are not about abstract submissions cannot be evidence for a
    # conference abstract deadline, even when they contain an unrelated date.
    if kind=='conference' and not re.search(r'abstract|call for submissions|scientific\s+submission',text,re.I):
        return []
    return list({(h['field'],h['value'],h['evidence']):h for h in found}.values())

def source_targets(data):
    targets = {}
    for kind, collection in [('conference',data['conferences']),('award',data['awards'])]:
        for item in collection:
            urls = [item.get('url')]
            if kind == 'conference':
                urls += [item.get('guideline'), item.get('submissionSource')]
                urls += item.get('additionalSources') or []
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
    """Collect evidence; never edit conference or award records. Ambiguous
    candidates across one or multiple sources are quarantined as conflicts."""
    cache=cache or {}
    checked_at=checked_at or dt.datetime.now(dt.timezone.utc).isoformat()
    targets=list(source_targets(data).items())
    if limit is not None: targets=targets[:limit]
    output=[]; observed=[]; future_observed=[]; updated=dict(cache)
    # One-hop discovery of official abstract pages; no general web crawling.
    from .discovery import discover_abstract_links
    configured_urls={url for url,_ in targets}
    discovered_targets={}
    discovered_by_record={}
    discovered_sources=[]
    by_kind={'conference':{c['id']:c for c in data['conferences']},
             'award':{a['id']:a for a in data['awards']}}
    for i,(url,records) in enumerate(targets):
        if i and delay:time.sleep(delay)
        prior=cache.get(url,{})
        try:
            page,is_html=fetcher(url,timeout=timeout)
            content=textify(page,is_html)
            if len(content)<70: raise ValueError('Source text too short for reliable monitoring')
            digest=hashlib.sha256(content.encode()).hexdigest()
            state='baseline' if not prior.get('digest') else 'changed' if prior['digest']!=digest else 'unchanged'
            for ref in records:
                record=by_kind[ref['kind']][ref['id']]
                year=int(ref['start'][:4]) if ref.get('start') else next((int(y) for y in re.findall(r'20\d{2}',ref['name'])),None)
                if ref['kind']=='award' and record.get('conferenceId'):
                    linked=by_kind['conference'].get(record['conferenceId'])
                    if linked and linked.get('start'):year=int(linked['start'][:4])
                for hit in extract_labeled_dates(content,ref['kind'],year,ref['name']):
                    observed.append({**hit,'record_type':ref['kind'],'record_id':ref['id'],
                                     'record_name':ref['name'],'source_url':url})
            # Discover future editions of the SAME curated conference series only.
            from .rollover import extract_future_meetings
            for ref in records:
                if ref['kind']=='conference':
                    parent=by_kind['conference'][ref['id']]
                    future_observed.extend(extract_future_meetings(content,parent,url,
                        today=dt.date.fromisoformat(checked_at[:10])))
            if is_html:
                for ref in records:
                    if ref['kind']!='conference':
                        continue
                    year=int(ref['start'][:4]) if ref.get('start') else next((int(y) for y in re.findall(r'20\d{2}',ref['name'])),None)
                    for link in discover_abstract_links(page,url,year,max_links=3):
                        if link['url'] in configured_urls:
                            continue
                        key=ref['id']
                        already=discovered_by_record.setdefault(key,set())
                        if link['url'] in already or len(already)>=2:
                            continue
                        already.add(link['url'])
                        discovered_targets.setdefault(link['url'],[]).append({
                            'kind':'conference','id':key,'name':ref['name'],
                            'start':ref.get('start'),'parent_url':url,
                            'link_label':link['label']})
            updated[url]={'digest':digest,'checked_at':checked_at,'length':len(content)}
            output.append({'url':url,'status':state,'records':records,'checked_at':checked_at,'proposed_count':0})
        except (HTTPError,URLError,TimeoutError,ValueError,OSError,UnicodeError) as error:
            output.append({'url':url,'status':'unavailable','records':records,'checked_at':checked_at,
                           'error':str(error)[:300],'proposed_count':0})
    # Follow only the best two qualifying links per conference, once each.
    # A discovered page is checked but never allowed to discover further pages.
    for i,(url,records) in enumerate(discovered_targets.items()):
        if delay:time.sleep(delay)
        prior=cache.get(url,{})
        try:
            page,is_html=fetcher(url,timeout=timeout)
            content=textify(page,is_html)
            if len(content)<70:
                raise ValueError('Discovered source text too short for reliable monitoring')
            digest=hashlib.sha256(content.encode()).hexdigest()
            state='baseline' if not prior.get('digest') else 'changed' if prior['digest']!=digest else 'unchanged'
            for ref in records:
                year=int(ref['start'][:4]) if ref.get('start') else next((int(y) for y in re.findall(r'20\d{2}',ref['name'])),None)
                hits=extract_labeled_dates(content,ref['kind'],year,ref['name'])
                for hit in hits:
                    observed.append({**hit,'record_type':'conference','record_id':ref['id'],
                                     'record_name':ref['name'],'source_url':url})
                discovered_sources.append({
                    'record_type':'conference','record_id':ref['id'],
                    'source_url':url,'parent_url':ref['parent_url'],
                    'link_label':ref['link_label'],'extracted_fields':sorted({h['field'] for h in hits})})
            updated[url]={'digest':digest,'checked_at':checked_at,'length':len(content)}
            output.append({'url':url,'status':state,'records':records,
                           'checked_at':checked_at,'proposed_count':0,'discovered':True})
        except (HTTPError,URLError,TimeoutError,ValueError,OSError,UnicodeError) as error:
            output.append({'url':url,'status':'unavailable','records':records,
                           'checked_at':checked_at,'error':str(error)[:300],
                           'proposed_count':0,'discovered':True})
    grouped={}
    for hit in observed:
        grouped.setdefault((hit['record_type'],hit['record_id'],hit['field']),[]).append(hit)
    proposals=[];conflicts=[]
    for (kind,record_id,field),hits in grouped.items():
        values=sorted({h['value'] for h in hits})
        if len(values)>1:
            conflicts.append({'record_type':kind,'record_id':record_id,'record_name':hits[0]['record_name'],
                              'field':field,'values':values,'sources':[
                                  {'value':h['value'],'url':h['source_url'],'evidence':h['evidence']} for h in hits]})
            continue
        hit=hits[0];record=by_kind[kind][record_id]
        matching_sources=sorted({h['source_url'] for h in hits})
        old=record.get(field) or (record.get('opens') if kind=='award' and field=='open' else None)
        if old==hit['value']:continue
        # Do not propose implausible chronology or inferred post-meeting dates.
        v=hit['value']
        existing_open=(v if field=='open' else record.get('open') or record.get('opens'))
        existing_deadline=(v if field=='deadline' else record.get('deadline'))
        if existing_open and existing_deadline and existing_open>existing_deadline:continue
        if kind=='conference' and record.get('start') and field in ('open','deadline') and v>record['start']:
            continue
        proposals.append({
            'id':short_id(kind,record_id,field,v,hit['source_url']),
            'record_type':kind,'record_id':record_id,'record_name':hit['record_name'],
            'field':field,'current_value':old,'proposed_value':v,
            'source_url':hit['source_url'],'evidence':hit['evidence'],
            'corroborating_sources':matching_sources,
            'review_status':'requires_human_verification',
            'reason':'Missing published date' if not old else 'Source date differs from current record'})
    # Reject differing future dates for a single meeting edition.
    future_by_id={}
    for f in future_observed:
        future_by_id.setdefault(f['record_id'],[]).append(f)
    existing_ids={c['id'] for c in data['conferences']}
    future_candidates=[]; future_conflicts=[]
    for cid,hits in future_by_id.items():
        if cid in existing_ids:continue
        values={(h['start'],h['end']) for h in hits}
        if len(values)>1:
            future_conflicts.append({'record_id':cid,'values':sorted([list(x) for x in values])})
            continue
        hit=hits[0]
        hit['corroborating_sources']=sorted({h['source_url'] for h in hits})
        future_candidates.append(hit)
    proposals.sort(key=lambda x:(x['record_type'],x['record_id'],x['field'],x['proposed_value']))
    conflicts.sort(key=lambda x:(x['record_type'],x['record_id'],x['field']))
    for item in output:
        item['proposed_count']=sum(p['source_url']==item['url'] for p in proposals)
    coverage=[]
    for conf in data['conferences']:
        related=[item for item in output if any(
            r['kind']=='conference' and r['id']==conf['id']
            for r in item['records'])]
        reachable=sum(item['status']!='unavailable' for item in related)
        candidates=sorted({hit['field'] for hit in observed
            if hit['record_type']=='conference' and hit['record_id']==conf['id']})
        missing=[field for field in ('open','deadline') if not conf.get(field)]
        coverage.append({'record_id':conf['id'],'record_name':conf['name'],
                         'sources_attempted':len(related),'sources_reachable':reachable,
                         'discovered_pages':sum(bool(item.get('discovered')) for item in related),
                         'extracted_fields':candidates,'missing_fields':missing,
                         'needs_attention':bool(missing and
                             (reachable==0 or not set(missing).intersection(candidates)))})
    report={'schema_version':2,'checked_at':checked_at,'source_count':len(output),
            'counts':{k:sum(x['status']==k for x in output) for k in ('baseline','changed','unchanged','unavailable')},
            'checks':output,'proposals':proposals,'conflicts':conflicts,
            'discovered_sources':discovered_sources,'source_coverage':coverage,
            'future_candidates':future_candidates,'future_conflicts':future_conflicts,
            'publication':'Raw evidence only. Automatic publication is decided by a separate strict policy; conflicts are held.'}
    return report,updated

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
        for field in ('open','deadline','lateOpen','lateDeadline','start','end','deadlineTime','city','venue','location','state','country'):
            future[field]=None
        for field in ('fee','limit','limitType','limitNote','flag','presentationFormats','presentationPolicy','submissionCategoriesVerified'):
            future[field]=[] if field=='presentationFormats' else False if field=='submissionCategoriesVerified' else None
        future['types']=[]
        for field in ('url','guideline','submissionSource'):
            if future.get(field):
                future['priorCycleSource'+field.capitalize()]=future[field]
            future[field]=None
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
    if report.get('schema_version') != 2:
        raise ValueError('Legacy monitoring report is unsafe to approve; run the updated monitor to create a fresh report')
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
    if field not in ('open','deadline','lateOpen','lateDeadline'):
        raise ValueError('Date field not on update allowlist')
    if any(c['record_type']==p['record_type'] and c['record_id']==p['record_id'] and c['field']==field for c in report.get('conflicts',[])):
        raise ValueError('This date field has conflicting official evidence')
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
