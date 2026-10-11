"""Find likely abstract submission pages linked by a conference's official source.

This is a bounded, one-hop discovery pass, not a general-purpose web crawler.
Only same-host HTTPS pages with relevant link labels and an appropriate
meeting-site path qualify. Discovered URLs are only *evidence candidates*.
"""
from __future__ import annotations

from html.parser import HTMLParser
import re
from urllib.parse import urljoin, urldefrag, urlsplit

POSITIVE = re.compile(
    r'\b(?:abstracts?|submit(?:ting)?\s+(?:your\s+)?(?:science|research|abstracts?)|'
    r'call\s+for\s+(?:abstracts?|papers?|submissions?)|submission\s+(?:guidelines?|information|dates|deadline)|'
    r'important\s+dates|key\s+dates)\b', re.I)
NEGATIVE = re.compile(
    r'\b(?:past\s+meetings?|previous\s+year|archives?|abstract\s+books?|'
    r'abstract\s+categories|accepted\s+abstracts?|abstract\s+awards?|abstract\s+authors?|'
    r'oral\s+presentations?|posters?\s+session|privacy|member\s+login|social\s+media)\b',re.I)
PATH_RE = re.compile(
    r'(?:abstract|submission|call-for-|key-dates|important-dates|deadlines?)', re.I)
YEAR = re.compile(r'(?<!\d)20\d{2}(?!\d)')
# Society portals may list many unrelated meetings. Require the current
# source's event-specific path prefix, not merely the same broad domain.
GENERIC_PARTS={'en','meeting','meetings','events','education','meeting-calendar',
               'meetings-and-events','meetings-education','learning','micro-sites',
               'calendar','members','membership','about','professional',
               'professionals','resources','education-and-resources','conferences'}

class AnchorLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links=[]
        self.anchor=None
        self.depth=0
        self.skip=0

    def handle_starttag(self,tag,attrs):
        if tag in ('script','style','noscript','svg','template'):
            self.skip+=1
        if tag=='a' and not self.skip:
            args=dict(attrs)
            if self.anchor is None:
                self.anchor={'href':args.get('href',''),'text':[], 'title':args.get('title') or '',
                             'aria':args.get('aria-label') or ''}
                self.depth=1
            else:
                self.depth+=1

    def handle_endtag(self,tag):
        if tag=='a' and self.anchor is not None and not self.skip:
            self.depth-=1
            if self.depth<=0:
                self.links.append((self.anchor['href'],
                                   ' '.join(self.anchor['text']+[self.anchor['title'],self.anchor['aria']]).strip()))
                self.anchor=None
        if tag in ('script','style','noscript','svg','template'):
            self.skip=max(0,self.skip-1)

    def handle_data(self,text):
        if self.anchor is not None and not self.skip:
            self.anchor['text'].append(text)

class EventHeadings(HTMLParser):
    """Collect visible H1 headings to validate a dedicated event-site root."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.headings=[]
        self._in_heading=False
        self._text=[]
    def handle_starttag(self,tag,attrs):
        if tag=='h1':
            self._in_heading=True
            self._text=[]
    def handle_endtag(self,tag):
        if tag=='h1' and self._in_heading:
            self.headings.append(' '.join(' '.join(self._text).split()))
            self._in_heading=False
    def handle_data(self,data):
        if self._in_heading:
            self._text.append(data)

def _eligible_event_root(page, meeting_year, record_name):
    """Allow same-host discovery from / only for a clearly named event site.

    A general professional-society homepage must not authorize abstracts
    from other meetings merely because its navigation mentions a meeting year.
    """
    if not meeting_year or not record_name:
        return False
    event=' '.join(re.sub(r'\b20\d{2}\b','',record_name).casefold().split())
    if len(event)<12 or not re.search(rf'\b{int(meeting_year)}\b',page):
        return False
    parser=EventHeadings()
    parser.feed(page)
    return any(event in ' '.join(heading.casefold().split())
               for heading in parser.headings)
    
def discover_abstract_links(page, base_url, meeting_year=None, max_links=2, record_name=None):
    """Return sorted same-host candidate URLs, with their visible anchor text.

    Require a relevant abstract/submission anchor, and keep child links within
    the same meeting section of the site (e.g. /annualmeeting/abstracts/).
    Generic society-wide index pages are intentionally not used as evidence
    for one particular conference edition.
    """
    root=urlsplit(base_url)
    if root.scheme!='https' or not root.hostname or root.username or root.password:
        return []
    parser=AnchorLinks()
    parser.feed(page)
    path_segments=[s for s in root.path.split('/') if s]
    # Stop at the first event-specific path component. A generic /meetings/
    # index has no conference identity and cannot authorize linked dates.
    scope_end=next((i+1 for i,seg in enumerate(path_segments)
                    if seg.lower() not in GENERIC_PARTS),None)
    scope=[seg.lower() for seg in path_segments[:scope_end]] if scope_end else []
    # Root conference microsites, such as sheaspring.org, often put abstracts
    # under /attendees/abstracts/. Bound discovery by a matching event H1.
    root_event=not path_segments and _eligible_event_root(page, meeting_year, record_name)
    if not scope and not root_event:
        return []
    candidates={}
    for pos,(href,label) in enumerate(parser.links):
        label=' '.join(label.split())
        if not href or not label:continue
        if NEGATIVE.search(label):continue
        try:
            url,_=urldefrag(urljoin(base_url,href))
            parsed=urlsplit(url)
            if parsed.scheme!='https' or (parsed.hostname or '').lower()!=root.hostname.lower():
                continue
            if parsed.username or parsed.password or parsed.port not in (None,443):
                continue
            if url==base_url or parsed.path.rstrip('/')==root.path.rstrip('/'):
                continue
            if any(parsed.path.lower().endswith(ext) for ext in ('.pdf','.zip','.doc','.docx','.xlsx','.jpg','.png')):
                continue
            target_segments=[x.lower() for x in parsed.path.split('/') if x]
            if scope and target_segments[:len(scope)]!=scope:
                continue
            if root_event and not PATH_RE.search(parsed.path):
                continue
            # Year-specific links must match this conference's meeting edition.
            years={int(y) for y in YEAR.findall(parsed.path)}
            if meeting_year and years and int(meeting_year) not in years:
                continue
            strong=bool(re.search(r'\b(?:abstracts?|submit\s+(?:your\s+)?(?:science|abstracts?)|call\s+for\s+abstracts?)\b',label,re.I))
            if not POSITIVE.search(label) and not (strong or PATH_RE.search(parsed.path)):
                continue
            if not strong and not PATH_RE.search(parsed.path):
                continue

            priority=(4 if strong else 0)+(2 if PATH_RE.search(parsed.path) else 0)
            priority+=1 if 'abstract' in parsed.path.lower() else 0
            if url not in candidates or priority>candidates[url][0]:
                candidates[url]=(priority,pos,label[:150])
        except ValueError:
            continue
    chosen=sorted(candidates.items(),key=lambda pair:(-pair[1][0],pair[1][1]))
    return [{'url':url,'label':meta[2],'parent_url':base_url}
            for url,meta in chosen[:max(0,max_links)]]
