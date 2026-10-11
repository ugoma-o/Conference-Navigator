"""Annual meeting rollover: discover only explicitly dated future cycles on tracked official pages.

The roster of organizations stays curated. New records represent confirmed future
instances of existing conference series; never carry old submission deadlines.
"""
from __future__ import annotations
import datetime as dt
import re
from urllib.parse import urlparse

MONTHS={m.lower():i for i,m in enumerate(
    'January February March April May June July August September October November December'.split(),1)}
MONTH='|'.join(MONTHS)
RANGE=re.compile(
    rf'\b(?P<sm>{MONTH})\s+(?P<sd>\d{{1,2}})(?:st|nd|rd|th)?'
    rf'(?:,?\s+(?P<sy>20\d{{2}}))?\s*(?:-|–|—|to|through)\s*'
    rf'(?:(?P<em>{MONTH})\s+)?(?P<ed>\d{{1,2}})(?:st|nd|rd|th)?,?\s+'
    rf'(?P<ey>20\d{{2}})\b',re.I)
PROVISIONAL=re.compile(r'\b(?:tentative|expected|projected|estimated|anticipated|provisional|not confirmed|TBA|subject to change)\b',re.I)
EVENT=re.compile(r'\b(?:annual|meeting|conference|congress|symposium|scientific sessions?|summit|assembly|forum|converge|week|ENDO|CROI)\b',re.I)
IGNORED={'annual','meeting','conference','congress','symposium','scientific','sessions','summit','assembly','forum','week','of','the','and','on','in','for','exhibition','exhibitions','international'}

def series_year(record):
    """Require an explicitly year-labelled series to avoid inventing a cycle."""
    m=re.search(r'\b(20\d{2})\b',record.get('name',''))
    if m:return int(m.group(1))
    m=re.search(r'\b[A-Z]{2,8}\.(\d{2})\b',record.get('name',''))
    if m:return 2000+int(m.group(1))
    return None

def future_id(record,target_year):
    old_year=series_year(record)
    if not old_year:return None
    prior=record['id']
    if re.search(r'\d{2}$',prior):
        return prior[:-2]+str(target_year)[-2:]
    return prior+'-'+str(target_year)

def future_name(record,target_year):
    old=series_year(record)
    if old is None:return None
    n=record['name']
    if str(old) in n:return n.replace(str(old),str(target_year))
    return re.sub(r'\.'+str(old)[-2:]+r'\b','.'+str(target_year)[-2:],n,count=1)

def _identifies_meeting(context,name):
    stem=re.sub(r'\b20\d{2}\b|(?:\.[12]\d)\b','',name)
    tokens=[x for x in re.findall(r'[A-Za-z0-9]+',stem) if len(x)>1 and x.lower() not in IGNORED]
    if not tokens:return False
    # Shared-society pages (ASCO GI/GU, AHA sessions, SGIM regions) must
    # identify the specific submeeting, not merely the umbrella society.
    count=2 if tokens[0].upper() in {'ASCO','AHA','SGIM','AAPM','ACC'} else 1
    if len(tokens)<count:return False
    return all(re.search(r'\b'+re.escape(tok)+r'\b',context,re.I) for tok in tokens[:count])

def year_neutral_url(url,previous_year,target_year):
    if not url or urlparse(url).scheme!='https':return False
    path=urlparse(url).path.lower()
    old=str(previous_year)
    if old in path or str(target_year) in path:return str(target_year) in path
    # /am27 /aaem27 /2027-annual-meeting cannot be copied to 2028.
    if re.search(r'(?<!\d)'+str(previous_year)[-2:]+r'(?:/|$|[-_])',path):
        return False
    return True

def extract_future_meetings(text,record,source_url,today=None,max_years=3):
    """Return only short explicitly announced meeting-date ranges, not deadlines.

    text is core.textify output with literal ' . ' boundaries between HTML blocks.
    An event title/series identity must occur within the same or previous block.
    """
    current=series_year(record)
    if not current:return []
    today=today or dt.date.today()
    pieces=[s.strip() for s in re.split(r'\s+\.\s+',text) if s.strip()]
    seen={}
    for i,piece in enumerate(pieces):
        # Only the immediately preceding heading/block may provide meeting identity.
        lead=pieces[i-1][-145:]+' . ' if i else ''
        for match in RANGE.finditer(piece):
            y=int(match.group('ey'))
            if y<=current or y>min(current+max_years,today.year+4):continue
            if not year_neutral_url(source_url,current,y):continue
            try:
                first=dt.date(int(match.group('sy') or y),MONTHS[match.group('sm').lower()],int(match.group('sd')))
                last=dt.date(y,MONTHS[(match.group('em') or match.group('sm')).lower()],int(match.group('ed')))
            except (ValueError,KeyError):continue
            if not (first.year==y and first>=today and 1 <= (last-first).days <= 12):continue
            context=(lead+piece[max(0,match.start()-180):match.end()+65]).strip()
            if PROVISIONAL.search(context):continue
            if not EVENT.search(context):continue
            if not _identifies_meeting(context,record['name']):continue
            # Require meeting/event wording before the range, not an unrelated
            # event advertised after a date or a general page footer.
            prefix=context[:context.find(match.group())]
            if not EVENT.search(prefix):continue
            found={'priorCycleId':record['id'],'record_id':future_id(record,y),
                   'year':y,'name':future_name(record,y),'start':first.isoformat(),
                   'end':last.isoformat(),'source_url':source_url,'evidence':context[:380]}
            seen[(y,found['start'],found['end'])]=found
    return list(seen.values())

def make_cycle_record(parent,candidate,stamp):
    """Clone series identity only; all cycle-specific submission details start blank."""
    return {
        'id':candidate['record_id'],'name':candidate['name'],
        'society':parent['society'],'specialty':parent['specialty'],
        'start':candidate['start'],'end':candidate['end'],'city':'To be announced',
        'open':None,'deadline':None,'lateOpen':None,'lateDeadline':None,
        'deadlineTime':None,'limit':None,'limitType':None,'limitNote':None,
        'fee':None,'types':[],'url':candidate['source_url'],'guideline':None,
        'evidence':'official','flag':None,'note':'Meeting dates verified from the official organizer page; abstract dates and submission rules have not yet been announced.',
        'submissionCategoriesVerified':False,'presentationFormats':[],
        'priorCycleId':parent['id'],
        'fieldSources':{'start':{'url':candidate['source_url'],'checked_at':stamp,
                                'verified_by':'RISE future-cycle monitor','source_quote':candidate['evidence']},
                        'end':{'url':candidate['source_url'],'checked_at':stamp,
                              'verified_by':'RISE future-cycle monitor','source_quote':candidate['evidence']}}
    }
