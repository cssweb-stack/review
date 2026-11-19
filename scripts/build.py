from pathlib import Path
from collections import Counter
from html import escape,unescape
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
import json,re,shutil,os
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT.parent
SHARED=WORK/'css-shared/src'
OUT=ROOT/os.environ.get('REVIEW_OUTPUT', '_site')
HEADINGS_ONLY=os.environ.get('REVIEW_HEADINGS_ONLY')=='1'
OUT.mkdir(exist_ok=True)
for folder in ['heroes','redirects-404s']:(OUT/folder).mkdir(exist_ok=True)
def load(p,default=None):return json.loads(p.read_text()) if p.exists() else (default or {})
class Heading(HTMLParser):
 def __init__(self):super().__init__();self.active=False;self.found=False;self.parts=[]
 def handle_starttag(self,tag,attrs):
  if tag=='h1' and not self.found:self.active=True
 def handle_endtag(self,tag):
  if tag=='h1' and self.active:self.active=False;self.found=True
 def handle_data(self,text):
  if self.active:self.parts.append(text)
def first_heading(html):
 heading=Heading();heading.feed(html)
 return re.sub(r'\s+',' ',''.join(heading.parts)).strip()
def page(title,body):
 section='heroes' if title in ['Heroes','General Featured Images','Graduate Images','Current PUBA Images'] or title.endswith(' heroes') else 'redirects-404s' if title=='Redirects and 404s' or title.endswith(' redirects and 404s') else 'headings' if title.endswith(' page headings') else ''
 return '---\nlayout: layouts/review/shell.njk\ntitle: '+json.dumps(title)+'\nreviewSection: '+json.dumps(section)+'\n---\n'+body+'\n'

if not HEADINGS_ONLY:
 units=[]
 common=load(SHARED/'data/common/page-heroes.json').get('pages',{})
 for directory in sorted((SHARED/'data/units').iterdir()):
  key=directory.name;project=WORK/key
  if key=='style-guide' or not (project/'src').exists() or not (directory/'unit-details.json').exists():continue
  identity=load(directory/'unit-details.json');settings=load(directory/'site-settings.json');name=identity.get('shortName',key.upper());units.append((key,name))
  base='https://cssweb-stack.github.io/'+key
  migration=load(directory/'url-migration.json')
  evidence=load(SHARED/'data/common/original-public-urls.json').get(key,{})
  source_paths={unquote(item['path']).casefold():item['sources'] for item in evidence.get('paths',[])}
  body='<p>Links test the GitHub preview. Changes must be uploaded there before they can pass.</p>\n<h2>Redirects</h2>\n<ul>\n'
  if not load(SHARED/'data/common/redirect-policy.json').get('enabled', False):body='<p>Redirect generation is OFF during development. These are saved original-site mappings for launch, not active redirect pages.</p>\n<h2>Saved original-site mappings</h2>\n<ul>\n'
  if key=='pols':body='<p><a href="/final-review/pols.html">POLS final page-by-page review</a></p>\n'+body
  for row in migration.get('redirects',[]):
   proof=source_paths.get(unquote(row['from']).casefold(),[])
   original=settings.get('url',base).rstrip('/')+row['from']
   destination=row['to'] if row['to'].startswith('https://') else base+row['to']
   body+='<li><a href="'+escape(original,quote=True)+'">'+escape(row['from'])+'</a> → <a href="'+escape(destination,quote=True)+'">'+escape(row['to'])+'</a><br>Source evidence: '+escape('; '.join(Path(item.split(' (')[0]).name+(' (original article link)' if '(original article link)' in item else '') for item in proof) or 'Not verified')+'</li>\n'
  if not migration.get('redirects'):body+='<li>No redirects recorded yet.</li>\n'
  body+='</ul>\n<p>Source evidence confirms that the old address belongs to the original site. Saved destination choices still require launch review, including changes made while redirects are disabled.</p>\n<h2>Retired pages: expect 404</h2>\n<ul>\n'
  for row in migration.get('retired',[]):body+='<li><a href="'+escape(base+row['from'],quote=True)+'">'+escape(row.get('label') or row['from'])+'</a> '+escape(row['from'])+'</li>\n'
  if not migration.get('retired'):body+='<li>No retired pages recorded.</li>\n'
  body+='</ul>\n<h2>404 test</h2>\n<ul>\n<li><a href="'+base+'/review-missing-page-test/">Open a nonexistent page</a></li>\n</ul>\n'
  if migration.get('unresolved'):
   body+='<h2>Unresolved</h2>\n<ul>\n'
   for row in migration['unresolved']:body+='<li>'+escape(row['from'])+': '+escape(row.get('note','Decision pending'))+'</li>\n'
   body+='</ul>\n'
  (OUT/'redirects-404s'/f'{key}.html').write_text(page(name+' redirects and 404s',body))
  heroes=load(directory/'heroes.json');faculty=load(directory/'faculty-heroes.json').get('pages',{});groups={'Main Pages':[],'Faculty Landing Pages':[],'Faculty Bio Pages':[],'Privacy and Policies':[]}
  source_info={}
  for source in project.joinpath('src').rglob('*.html'):
   text=source.read_text();m=re.search(r'^permalink:\s*["\']?([^"\'\n]+)',text,re.M)
   if not m:continue
   url=m[1];title=re.search(r'^title:\s*["\']?(.*?)["\']?$',text,re.M);title=title[1] if title else url
   built=project/'_site'/('index.html' if url=='/' else url.lstrip('/')+('index.html' if url.endswith('/') else ''))
   title=first_heading(text) or title
   image=None;position='center center'
   if built.exists():
    b=built.read_text();title=first_heading(b) or first_heading(text) or title;section=re.search(r'<section\b[^>]*class="page-hero[^>]*>(.*?)</section>',b,re.S)
    if section:
     full=section[0];im=re.search(r'background-image:\s*url\([\'"]?([^\'"\)]+)',full)
     if im:image=im[1]
     pm=re.search(r'--hero-position:\s*([^;]+)',full)
     if pm:position=pm[1]
   assigned=common.get(url) or heroes.get('pages',{}).get(url) or faculty.get(url) or {}
   if common.get(url):image=common[url]['image']
   elif 'personSlug:' in text or re.search(r'^layout:.*(?:faculty-profile|person-profile)',text,re.M) or url in faculty:
    image=load(SHARED/'data/common/page-heroes.json').get('facultyBio',{}).get('image',image)
   if not image:image=assigned.get('image') or heroes.get('defaultHero') or settings.get('defaultHero')
   if position=='center center':position=assigned.get('position','center center')
   if url in ['/policies-procedures.html','/privacy.html','/404.html']:
    group='Privacy and Policies'
   elif 'personSlug:' in text or re.search(r'^layout:.*(?:faculty-profile|person-profile)',text,re.M) or url in faculty:
    group='Faculty Bio Pages'
   elif url.startswith('/faculty/') or url in ['/faculty.html','/associated-faculty.html']:
    group='Faculty Landing Pages'
   else:
    group='Main Pages'
   if key=='soc' and group=='Main Pages':
    group='Graduate Pages' if url.startswith('/graduate/') else 'Undergraduate Pages' if url.startswith('/undergraduate/') or url=='/alpha-kappa-delta.html' else 'General Pages'
   if key=='ssri' and group=='Main Pages':
    group='Support' if url.startswith('/support/') else 'Research' if url.startswith('/research/') else 'Other Pages'
   groups.setdefault(group,[]).append((title,url,image,position))
   published=re.search(r'^published:\s*[\"\']?([^\"\'\n]+)',text,re.M)
   source_info[url]={'source':str(source.relative_to(project/'src')),'profile':group=='Faculty Bio Pages','news':bool(published) and '/news/' in url,'published':published[1] if published else ''}
  def image_key(row):
   return re.sub(r'^/'+re.escape(key)+r'(?=/media/)','',urlsplit(row[2]).path) if row[2] else ''
  from hero_groups import group_heroes,duplicate_hero_urls
  all_rows=[row for rows in groups.values() for row in rows]
  sections,news_notes=group_heroes(all_rows,source_info,load(directory/'navigation.json',[]),load(directory/'degree-navigation.json'),load(directory/'news-settings.json').get('indexUrl','/news/'),key)
  duplicate_urls=duplicate_hero_urls(sections,key)
  displayed=[row for _,rows,_ in sections for row in rows]
  unit_counts=Counter(image_key(row) for row in displayed if row[2])
  use_counts={row[1]:unit_counts[image_key(row)] if row[2] else 0 for row in displayed}
  body='<p>Red outlines mark duplicate image choices on replaceable pages. Fixed Pages stay unmarked; faculty pages, news article samples and privacy/policies/404 do not count toward duplicate warnings.</p>\n<ul>\n'+''.join('<li><a href="#'+re.sub(r'[^a-z0-9]+','-',group.lower()).strip('-')+'">'+escape(group)+'</a></li>\n' for group,_,_ in sections)+'</ul>\n'
  for group,rows,level in sections:
   anchor=re.sub(r'[^a-z0-9]+','-',group.lower()).strip('-')
   body+='<hr>\n<h'+str(level)+' id="'+anchor+'">'+escape(group)+'</h'+str(level)+'>\n'
   if group=='Fixed Pages':body+='<p>Home, Courses, Contact and Support: fixed review group. Preserve these image choices unless a change is explicitly requested.</p>\n'
   if group in news_notes:
    note=news_notes[group]
    if not note['mismatches']:body+='<p>Verified all '+str(note['total'])+' news articles use the same hero image as <a href="'+escape(base+note['index'],quote=True)+'">the main news page</a>. One representative article is shown below.</p>\n'
    else:body+='<p>Checked '+str(note['total'])+' news articles; '+str(len(note['mismatches']))+' do not match the main news hero. Exceptions are shown for review.</p>\n'
   for title,url,image,position in rows:
    clean_image=re.sub(r'^/'+re.escape(key)+r'(?=/media/)','',urlsplit(image).path) if image else None
    count=use_counts[url]
    duplicate=url in duplicate_urls
    body+='<div class="hero-entry">\n<p>'+escape(title)+' · <a href="'+escape(base+url,quote=True)+'">'+escape(url)+'</a> · <span title="Uses among displayed review entries; news articles are represented once">'+escape(Path(urlsplit(image).path).name if image else 'No hero assigned')+' ('+str(count)+')</span>'+(' <strong class="review-hero-label review-hero-label--featured">'+('Graduate ' if '/students/graduate/' in image else '')+'Featured</strong>' if image and '/featured/' in image else ' <strong class="review-hero-label">'+('Graduate ' if '/students/graduate/' in image else '')+'Supporting</strong>' if image and '/supporting/' in image else '')+'</p>\n'
    if duplicate:body+='<p><strong>Duplicate — review image choice</strong></p>\n'
    if image:
     clean=urlsplit(image).path;clean=re.sub(r'^/'+re.escape(key)+r'(?=/media/)','',clean)
     candidates=[SHARED/clean.lstrip('/'),project/'src'/clean.lstrip('/'),project/'_site'/clean.lstrip('/')]
     asset=next((p for p in candidates if p.is_file()),None)
     if asset:
      target=OUT/'heroes'/'media'/key/clean.lstrip('/');target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(asset,target)
      href='media/'+key+'/'+clean.lstrip('/')
      body+='<img class="review-hero-image'+(' review-hero-image--duplicate' if duplicate else '')+'" src="'+escape(href,quote=True)+'" alt="'+escape(title+' hero image',quote=True)+'">\n'
     else:body+='<p>Image file unavailable: '+escape(image)+'</p>\n'
    else:body+='<p>No hero assigned.</p>\n'
    body+='</div>\n'
  (OUT/'heroes'/f'{key}.html').write_text(page(name+' heroes',body))
  if key=='puba':
   unique_images=sorted({row[2] for rows in groups.values() for row in rows if row[2]})
   body=''
   for image in unique_images:
    clean=re.sub(r'^/puba(?=/media/)','',urlsplit(image).path)
    href='media/puba/'+clean.lstrip('/')
    body+='<div class="hero-entry">\n<p>'+escape(Path(clean).name)+' · '+escape(str(Path(clean).parent).removeprefix('/media/heroes/'))+'</p>\n<img class="review-hero-image" src="'+escape(href,quote=True)+'" alt="PUBA hero image '+escape(Path(clean).name,quote=True)+'">\n</div>\n'
   (OUT/'heroes/puba-images.html').write_text(page('Current PUBA Images',body))

 # Approved General Featured bank for choosing images on any unit site.
 body=''
 for asset in sorted((SHARED/'media/heroes/students/general/featured').glob('*.webp'),key=lambda p:p.name):
  clean=str(asset.relative_to(SHARED));target=OUT/'heroes/media/featured-review'/clean;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(asset,target)
  href='media/featured-review/'+clean
  body+='<div class="hero-entry">\n<p>'+escape(asset.name)+'</p>\n<img class="review-hero-image" src="'+escape(href,quote=True)+'" alt="Student hero image '+escape(asset.stem,quote=True)+'">\n</div>\n'
 (OUT/'heroes/general-featured.html').write_text(page('General Featured Images',body))
 body=''
 for category,label in [('featured','Featured'),('supporting','Supporting')]:
  assets=sorted((SHARED/'media/heroes/students/graduate'/category).glob('*.webp'),key=lambda p:p.name)
  if not assets:continue
  body+='<hr>\n<h2>'+label+'</h2>\n'
  for asset in assets:
   clean=str(asset.relative_to(SHARED));target=OUT/'heroes/media/graduate-review'/clean;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(asset,target)
   href='media/graduate-review/'+clean
   body+='<div class="hero-entry">\n<p>'+escape(asset.name)+'</p>\n<img class="review-hero-image" src="'+escape(href,quote=True)+'" alt="Graduate hero image '+escape(asset.stem,quote=True)+'">\n</div>\n'
 (OUT/'heroes/graduate-images.html').write_text(page('Graduate Images',body))
# Headings are read from built content pages, not metadata titles or redirects.
def navigation_urls(items):
 for item in items:
  url=item.get('url','')
  if url.startswith('/') and not url.startswith('//'):yield urlsplit(url).path
  yield from navigation_urls(item.get('children',[]))
def pols_page_groups(urls):
 remaining=set(urls);groups=[]
 def add(label,ordered):
  selected=[url for url in ordered if url in remaining]
  if selected:groups.append((label,selected));remaining.difference_update(selected)
 order=list(dict.fromkeys(navigation_urls(load(SHARED/'data/units/pols/navigation.json',[]))))
 def matching(prefix):return [url for url in order if url.startswith(prefix)]+sorted(url for url in remaining if url.startswith(prefix) and url not in order)
 add('Main Pages',[url for url in order if not url.startswith(('/undergraduate/','/graduate/','/about/specializations/','/faculty/'))])
 add('Specializations',matching('/about/specializations/'))
 add('Undergraduate',matching('/undergraduate/'))
 for family in load(SHARED/'data/units/pols/degree-navigation.json').values():add(family['label']+' · Shared Navigation',[row['url'] for row in family['pages']])
 add('Graduate Resources',matching('/graduate/'))
 add('Faculty',matching('/faculty/'))
 add('Other Pages',sorted(remaining))
 return groups
# One comparison page per reviewed unit. Read current rendered values only.
(OUT/'headings').mkdir(exist_ok=True)
for stale in [OUT/'headings.html',ROOT/'_site/headings.html']:
 if stale.exists():stale.unlink()
for key in load(SHARED/'data/common/review-units.json')['current']:
 project=WORK/key;headings={};source_paths={};page_titles={};source_texts={}
 label=load(SHARED/'data/common/title-standards.json')['units'][key]
 for source in sorted((project/'src').rglob('*.html')):
  text=source.read_text();m=re.search(r'^permalink:\s*[\"\']?([^\"\'\n]+)',text,re.M)
  if not m:continue
  url=m[1];built=project/'_site'/('index.html' if url=='/' else url.lstrip('/')+('index.html' if url.endswith('/') else ''))
  rendered=built.read_text() if built.is_file() else ''
  if rendered.startswith('<!-- Generated by shared URL migration; do not edit. -->'):continue
  headings[url]=first_heading(rendered)
  title_match=re.search(r'<title\b[^>]*>(.*?)</title>',rendered,re.S|re.I)
  page_titles[url]=unescape(re.sub(r'\s+',' ',title_match[1]).strip()) if title_match else 'Missing page title'
  source_paths[url]=str(source.relative_to(project/'src'));source_texts[url]=text
 nav=list(dict.fromkeys(url for url in navigation_urls(load(SHARED/'data/units'/key/'navigation.json',[])) if url in headings))
 remaining=sorted(set(headings)-set(nav),key=lambda url:(headings[url].casefold(),url))
 order=nav+remaining
 groups={}
 def folder_label(folder):
  labels={'about':'About','undergraduate':'Undergraduate','graduate':'Graduate','faculty':'Faculty Directories','master-ma':'MA','doctorate-phd':'PhD','masters-mpa':'MPA','news':'News Pages'}
  return labels.get(folder,folder.replace('-',' ').title())
 for url in order:
  folders=source_paths[url].split('/')[:-1];text=source_texts[url]
  is_profile=bool(re.search(r'^personSlug:|^layout:.*(?:faculty-profile|person-profile)',text,re.M))
  is_news=bool(re.search(r'^newsImage:|^published:',text,re.M)) and ('news' in folders or 'news/' in url)
  if is_profile:group='Individual Faculty Profiles'
  elif is_news:group='News Articles'
  elif not folders:group='Main Pages'
  else:group=' / '.join(folder_label(part) for part in folders)
  groups.setdefault(group,[]).append(url)
 def group_order(group):
  if group=='Individual Faculty Profiles':return (8,group)
  if group=='News Articles':return (9,group)
  prefixes={'Main Pages':0,'About':1,'Undergraduate':2,'Graduate':3,'MPA':3,'Faculty Directories':4,'News Pages':5}
  return (prefixes.get(group.split(' / ')[0],6),group)
 body='<table class="review-heading-table" data-review-unit="'+key+'">\n<caption class="visually-hidden">'+escape(label)+' page titles, H1s and source filenames grouped by folder</caption>\n<thead class="visually-hidden">\n<tr>\n<th scope="col">Page Title</th>\n<th scope="col">H1</th>\n<th scope="col">Source Filename</th>\n</tr>\n</thead>\n'
 for group in sorted(groups,key=group_order):
  body+='<tbody data-page-group="'+escape(group,quote=True)+'">\n'
  if group!='Main Pages':body+='<tr class="review-heading-group">\n<th colspan="3"><h2>'+escape(group)+'</h2></th>\n</tr>\n'
  for url in groups[group]:
   body+='<tr data-page-path="'+escape(url,quote=True)+'">\n<td><a href="https://cssweb-stack.github.io/'+key+escape(url,quote=True)+'">'+escape(page_titles[url])+'</a></td>\n<td>'+escape(headings[url] or 'Missing H1')+'</td>\n<td>'+escape(source_paths[url])+'</td>\n</tr>\n'
  body+='</tbody>\n'
 body+='</table>\n'
 (OUT/'headings'/f'{key}.html').write_text(page(label+' page headings',body))

if HEADINGS_ONLY:
 print('Updated naming inventories only; hero/grid inventories unchanged.')
 raise SystemExit(0)

# Final walkthrough uses the same degree-navigation order as the unit.
(OUT/'final-review').mkdir(exist_ok=True)
project=WORK/'pols';current={}
for source in sorted((project/'src').rglob('*.html')):
 text=source.read_text();match=re.search(r'^permalink:\s*["\']?([^"\'\n]+)',text,re.M)
 if not match:continue
 url=match[1];built=project/'_site'/('index.html' if url=='/' else url.lstrip('/')+('index.html' if url.endswith('/') else ''))
 current[url]=first_heading(built.read_text()) if built.exists() else 'Build required'
body='<p>Review each page. MA and PhD pages are grouped in their shared navigation order.</p>\n<p><a href="/redirects-404s/pols.html">Redirects and 404 tests</a> · <a href="/headings/pols.html">Page headings and search titles</a></p>\n'
for label,urls in pols_page_groups(current):
 body+='<h2>'+escape(label)+'</h2>\n<ul>\n'
 for url in urls:body+='<li><a href="https://cssweb-stack.github.io/pols'+escape(url,quote=True)+'">'+escape(current[url])+'</a></li>\n'
 body+='</ul>\n'
(OUT/'final-review/pols.html').write_text(page('POLS Final Page Review',body))

# Rules use the shared document itself, rather than a second copy of its contents.
(OUT/'rules').mkdir(exist_ok=True)
# Render the editable shared document during each Eleventy build, never a copied snapshot.
legacy_rules=OUT/'rules/code-formatting.md'
if legacy_rules.exists():legacy_rules.unlink()
(OUT/'rules/code-formatting.html').write_text(page('Code Formatting', '{{ "code-cleanup.md" | readRuleDocument | renderContent("md") | safe }}').replace('reviewSection: ""','reviewSection: "rules"',1))
(OUT/'rules/language-writing.html').write_text(page('Language & Writing', '{{ "language-writing.md" | readRuleDocument | renderContent("md") | safe }}').replace('reviewSection: ""','reviewSection: "rules"',1))
(OUT/'rules.html').write_text(page('Rules','<p>Agreed rules for building and reviewing our websites. Select a rule set above.</p>').replace('reviewSection: ""','reviewSection: "rules"',1))
for folder,title in [('heroes','Heroes'),('redirects-404s','Redirects and 404s')]:
 body=''
 (OUT/folder/'index.html').write_text(page(title,body))
(OUT/'index.html').write_text(page('Review','<ul>\n<li><a href="redirects-404s/index.html">Redirects and 404s</a></li>\n<li><a href="heroes/index.html">Heroes</a></li>\n<li><a href="grids.html">Sidebars Left &amp; Right</a></li>\n</ul>').replace('href="../','href="'))
from grid_page import build_grid_page
build_grid_page(OUT,page)
from asset_link_pages import build_asset_link_pages
build_asset_link_pages(OUT,page,WORK,SHARED)
print('Built Review:',len(units),'units in each section.')
