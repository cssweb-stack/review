from html.parser import HTMLParser
from pathlib import Path
import re
root=Path(__file__).resolve().parents[2]
class Node:
 def __init__(self,tag='',attrs=(),parent=None):self.tag=tag;self.attrs=dict(attrs);self.children=[];self.parent=parent
 @property
 def cls(self):return self.attrs.get('class','').split()
class Tree(HTMLParser):
 def __init__(self):super().__init__();self.root=Node();self.stack=[self.root]
 def handle_starttag(self,t,a):
  n=Node(t,a,self.stack[-1]);self.stack[-1].children.append(n)
  if t not in ['area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr']:self.stack.append(n)
 def handle_endtag(self,t):
  for i in range(len(self.stack)-1,0,-1):
   if self.stack[i].tag==t:self.stack=self.stack[:i];break
 def walk(self,n=None):
  for c in (n or self.root).children:yield c;yield from self.walk(c)
layouts=['grid-welcome','grid-two','grid-three','grid-four','grid-five','grid-profile','grid-standard','grid-compact','grid-advisors','advising-grid','advising-person','program-button-sets','news-feed-grid','list-columns-two']
def norm(cls):return ' '.join(c for c in cls if not re.match(r'^(?:mb|mt|mx|my|p[xy]?)-',c))
def collect():
 patterns={};pages=[]
 for u in ['ssri','puba','es','anth','soc']:
  for f in sorted((root/u/'src').rglob('*.html')):
   m=re.search(r'^permalink:\s*[\"\']?([^\"\'\n]+)',f.read_text(),re.M)
   if not m:continue
   url=m[1];b=root/u/'_site'/('index.html' if url=='/' else url.lstrip('/')+('index.html' if url.endswith('/') else ''))

   if not b.is_file():raise RuntimeError(f'Build {u} before Review: missing {b.relative_to(root)}')
   p=Tree();p.feed(b.read_text());page={'unit':u,'url':url,'source':str(f.relative_to(root/u)),'patterns':[]};pages.append(page)
   for n in p.walk():
    parent=n;inside=False;record_layout=False
    while parent:
     if parent.tag=='table' or 'people-directory' in parent.cls:record_layout=True
     if parent.tag=='main':inside=True;break
     parent=parent.parent
    if not inside or record_layout:continue
    if not ('row' in n.cls or any(c in layouts for c in n.cls)):continue
    children=[norm(c.cls) for c in n.children]
    if 'row' in n.cls and (not children or all(c=='col-12' for c in children)):
     # One-column resource rows still change through container queries.
     if 'course-resource-grid' not in n.cls:continue
    # Repeated equal columns differ only by item count; retain count as evidence.
    equal=len(set(children))==1
    context = norm(n.parent.cls) if n.parent and 'course-resource-grid' in n.cls else ''
    sig=context+' / '+norm(n.cls)+' > '+ ('REPEAT '+children[0] if equal and children else ' | '.join(children))
    if sig not in patterns:patterns[sig]={'classes':norm(n.cls),'context':context,'children':children,'uses':[],'counts':[]}
    pat=patterns[sig];ref={'unit':u,'url':url};
    if ref not in pat['uses']:pat['uses'].append(ref)
    pat['counts'].append(len(n.children));page['patterns'].append(sig)
 return {'pages':pages,'patterns':list(patterns.values())}
