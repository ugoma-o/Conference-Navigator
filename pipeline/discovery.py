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
                self.anchor={'href':args.get('href',''),'text':[], 'title':args.get('title',''),
                             'aria':args.get('aria-label','')}
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

def discover_abstract_links(page, base_url, meeting_year=None, max_links=2):
    """Return sorted same-host candidate URLs, with their visible anchor text.

    Require a relevant abstract/submission anchor, and keep child links within
    the same meeting section of the site (e.g. /annualmeeting/abstracts/).
    For site root URLs, only strongly abstract-labelled links qualify.
    """
    root=urlsplit(base_url)
    if root.scheme!='https' or not root.hostname or root.username or root.password:
        return []
    parser=AnchorLinks()
    parser.feed(page)
    path_segments=[s for s in root.path.split('/') if s]
    # The first segment scopes navigation to an event section if available.
    site_section=path_segments[0].lower() if path_segments else None
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
            target_section=next((x.lower() for x in parsed.path.split('/') if x),None)
            if site_section and target_section!=site_section:
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
            if not site_section and not strong:
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
