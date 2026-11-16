"""Build Review's grid specimens from the five sites' rendered layout signatures."""
from html import escape
import json
from pathlib import Path
from grid_inventory import collect, SIDEBAR_CLASSES

def family(p):
 c=p['classes'];ch=' | '.join(p['children'])
 if c in SIDEBAR_CLASSES:return 'Sidebars Left & Right'
 if 'advising' in c or 'program-button' in c:return 'Combined Layouts'
 if 'list-columns' in c or 'course-resource' in c:return 'Equal Columns'
 if 'grid-five' in c or 'faculty-portrait-grid' in c:return 'Cards & Tiles'
 if 'row-cols' in c:return 'Equal Columns'
 if len(set(p['children']))==1:return 'Equal Columns'
 if 'image-text' in c or 'profile-page' in c or 'graduate-student' in c or 'unit-contact' in c:return 'Sidebars Left & Right'
 if len(p['children'])==2:return 'Sidebars Left & Right'
 return 'Combined Layouts'

def priority(p):
 # Show broadly reused arrangements before their narrower variants.
 units=len({use['unit'] for use in p['uses']})
 if p['classes'] in SIDEBAR_CLASSES:return (0,SIDEBAR_CLASSES.index(p['classes']),0,p['name'])
 return (1,-units,-len(p['uses']),p['name'])

def is_sidebar_column(classes):
 return any(token in classes.split() for token in ['review-sidebar','profile-sidebar','image-text-media','unit-contact-office','student-photo-column','col-md-3','col-xl-3'])

def name(p):
 if p['classes'] in SIDEBAR_CLASSES:return '.'+p['classes']
 if family(p)=='Sidebars Left & Right':
  return 'Sidebar — '+('left' if is_sidebar_column(p['children'][0]) else 'right')
 c=p['classes'];ch=' | '.join(p['children'])
 if 'faculty-portrait-grid' in c:return 'People cards — '+('1 / 2 / 3 / 4 / 5 columns' if 'row-cols-xl-4' in c else '1 / 2 / 3 / 5 columns')
 if 'row-cols-md-2 row-cols-xl-4' in c:return 'Cards — 1 / 2 / 4 columns'
 if 'row-cols-sm-2' in c:return 'Cards — 1 / 2 / 4, earlier transition'
 if 'grid-five' in c:return 'Tiles — '+('photo' if 'photo-tile' in ch else 'academic')+' — 1 / 3 / 5 columns'
 if 'advising-grid' in c:return 'Advising — paired people'
 if 'advising-person' in c:return 'Advising — photo / details'
 if 'list-columns-two' in c:return 'List — two flowing columns'
 if 'course-resource' in c:return 'Resource buttons — '+('three' if '--three' in p['context'] else 'two')
 if 'program-button' in c:return 'Program buttons — '+('stacked' if '--stacked' in c else 'sidebar')
 if 'col-lg-4' in ch:return 'Programs — introduction plus four tiles'
 if 'col-xl-6' in ch:return 'Introduction plus two sidebars — 50 / 25 / 25'
 if 'col-xl-9' in ch:return 'Introduction / sidebar — 75 / 25'
 if 'col-lg-10' in ch:return 'Text / image — 83 / 17'
 return 'Images — three equal columns'

def cell(label):
 return '<div class="review-grid-cell">\n<p>'+escape(label)+'</p>\n<p>'+escape(label+' · '+label+' · '+label)+'</p>\n</div>\n'

def advising_person():
 return '<section class="advising-person">\n<div class="advising-photo">\n'+cell('Photo')+'</div>\n<div class="advising-details">\n'+cell('Advisor details')+'</div>\n</section>\n'

def specimen(p):
 c=p['classes'];children=p['children'];output=''
 if family(p)=='Sidebars Left & Right':
  text=json.loads((Path(__file__).resolve().parents[1]/'data/grid-placeholder.json').read_text())
  output='<div class="'+c+'">\n'
  for classes in children:
   sidebar=is_sidebar_column(classes)
   label='Sidebar' if sidebar else 'Content area'
   paragraph=text['sidebar' if sidebar else 'content']
   output+='<div class="'+classes+'">\n<div class="review-grid-cell">\n<p>'+label+'</p>\n<p>'+escape(paragraph)+'</p>\n</div>\n</div>\n'
  return output+'</div>\n'
 if 'advising-grid' in c:return '<div class="'+c+'">\n'+advising_person()*2+'</div>\n'
 if c=='advising-person':
  # Preserve its real ancestor: its proportions change with the paired layout.
  return '<div class="advising-grid">\n'+advising_person()*2+'</div>\n'
 if 'list-columns-two' in c:return '<ul class="'+c+'">\n'+''.join('<li>Two-column list — item '+str(i)+'</li>\n' for i in range(1,9))+'</ul>\n'
 if 'course-resource' in c:
  count=3 if '--three' in p['context'] else 2
  return '<nav class="'+p['context']+'" aria-label="'+escape(name(p),quote=True)+'">\n<div class="'+c+'">\n'+''.join('<div class="col-12">\n'+cell('Resource '+str(i))+'</div>\n' for i in range(1,count+1))+'</div>\n</nav>\n'
 if 'grid-five' in c:
  output='<div class="'+c+'">\n'
  for i in range(7):
   if 'photo-tile' in ' '.join(children):
    output+='<div class="program-tile photo-tile tile-style tile-teal">\n<img class="photo-tile-image" src="/assets/grid-placeholder.svg" alt="" width="600" height="600">\n<span class="photo-tile-label">Photo tile '+str(i+1)+(' — longer wrapping label' if i==0 else '')+'</span>\n</div>\n'
   else:
    output+='<div class="program-tile tile-style tile-blue">\n<span class="program-tile-title">Tile '+str(i+1)+'</span>\n<span class="program-tile-label">Academic tile</span>\n</div>\n'
  return output+'</div>\n'
 if 'program-button' in c:
  buttons='<div class="'+c+'">\n'+''.join('<div class="'+ch+'">\n'+cell('Button group '+str(i+1))+'</div>\n' for i,ch in enumerate(children))+'</div>\n'
  if '--stacked' in c:
   return '<div class="row gy-4 gx-0 gx-md-5">\n<div class="col-12 col-xl-6">\n'+cell('Main content')+'</div>\n<div class="col-12 col-md-6 col-xl-3">\n'+cell('Supporting column')+'</div>\n<div class="col-12 col-md-6 col-xl-3">\n'+buttons+'</div>\n</div>\n'
  return '<div class="sidebar-right-med">\n<div class="profile-biography">\n'+cell('Main content')+'</div>\n<div class="profile-sidebar sidebar-resources">\n'+buttons+'</div>\n</div>\n'
 if 'row-cols' in c:children=[children[0]]*7
 output='<div class="'+c+'">\n'
 for i,ch in enumerate(children):
  label='Column '+str(i+1)
  if 'profile-sidebar' in ch:label='Sidebar'
  elif 'profile-biography' in ch:label='Main content'
  elif 'unit-contact-office' in ch:label='Office'
  elif 'unit-contact-map' in ch:label='Map'
  output+='<div class="'+ch+'">\n'+cell(label)+'</div>\n'
 return output+'</div>\n'

def build_grid_page(out,page):
 inventory=collect()
 patterns=inventory['patterns']
 for i,p in enumerate(patterns):p.update(id='grid-'+str(i+1),name=name(p),family=family(p))
 body=''
 body+='<p>General page layouts from SSRI, PUBA, Ethnic Studies, Anthropology and Sociology. Resize this page or open it on another device to compare their columns and gaps.</p>\n'
 body+='<p>These examples use the existing shared styles. The six sidebar layouts are standardized; other layout groups remain under review. Responsive data tables and record directories are reviewed separately. Colored cells are placeholders. Seven cards reveal incomplete rows.</p>\n'
 body+='<p><strong>'+str(len(inventory['pages']))+' pages inventoried · '+str(len(patterns))+' layout signatures</strong></p>\n'
 groups=[('sidebars','Sidebars Left & Right','Three sizes on each side, sharing one 33px gap and responsive progression.'),('equal-columns','Equal Columns','Equal-width rows with two, three or four columns, resource buttons and flowing lists.'),('cards-tiles','Cards & Tiles','Faculty and contact portrait grids, photo tiles and academic program tiles.'),('combined-layouts','Combined Layouts','Homepage arrangements and nested layouts such as paired advisors and sidebar button groups.')]
 body+='<div class="review-grid-tabs" role="tablist" aria-label="Layout patterns" hidden>\n'
 for key,label,intro in groups:
  body+='<button type="button" role="tab" id="tab-'+key+'" aria-controls="'+key+'" aria-selected="false" tabindex="-1">'+escape(label)+'</button>\n'
 body+='</div>\n'
 for key,label,intro in groups:
  body+='<section id="'+key+'" data-grid-panel aria-labelledby="tab-'+key+'">\n<h2>'+escape(label)+'</h2>\n<p>'+escape(intro)+' Common patterns appear first.</p>\n'
  for p in sorted(patterns,key=priority):
   if p['family']!=label:continue
   body+='<section class="review-grid-example" id="'+p['id']+'">\n<h3 id="'+p['id']+'-title">'+escape(p['name'])+'</h3>\n'
   body+='<p class="review-grid-reading" data-grid-reading="'+p['id']+'">Resize to compare the shared column arrangement.</p>\n'
   body+='<div class="review-grid-stage" data-grid-id="'+p['id']+'" data-grid-selector=".'+'.'.join(p['classes'].split())+'">\n'+specimen(p)+'</div>\n'
   body+='<details>\n<summary>Used on '+str(len(p['uses']))+' pages · classes</summary>\n<p><code>'+escape(p['classes'])+'</code></p>\n<ul>\n'
   for use in p['uses']:body+='<li><a href="https://cssweb-stack.github.io/'+use['unit']+use['url']+'">'+escape(use['unit'].upper()+' '+use['url'])+'</a></li>\n'
   body+='</ul>\n</details>\n</section>\n'
  body+='</section>\n'
 body+='<script src="/assets/js/review-grids.js" defer></script>\n'
 (out/'grids.html').write_text(page('Grids',body))
 (out/'grids-inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
 print('Grid inventory:',len(inventory['pages']),'pages,',len(patterns),'signatures.')
