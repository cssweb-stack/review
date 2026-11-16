"""Build Review's grid specimens from the five sites' rendered layout signatures."""
from html import escape
import json
from grid_inventory import collect

def family(p):
 c=p['classes'];ch=' | '.join(p['children'])
 if 'advising' in c or 'program-button' in c:return 'Combined Layouts'
 if 'list-columns' in c or 'course-resource' in c:return 'Equal Columns'
 if 'grid-five' in c or 'faculty-portrait-grid' in c:return 'Cards & Tiles'
 if 'row-cols' in c:return 'Equal Columns'
 if len(set(p['children']))==1:return 'Equal Columns'
 if 'image-text' in c or 'profile-page' in c or 'graduate-student' in c or 'unit-contact' in c:return 'Sidebars'
 if len(p['children'])==2:return 'Sidebars'
 return 'Combined Layouts'

def priority(p):
 # Show broadly reused arrangements before their narrower variants.
 units=len({use['unit'] for use in p['uses']})
 return (-units,-len(p['uses']),p['name'])

def name(p):
 c=p['classes'];ch=' | '.join(p['children'])
 if 'not-found-grid' in c:return 'Sidebar — 404'
 if 'unit-contact' in c:return 'Sidebar — office / map'
 if 'graduate-student' in c:return 'Sidebar — graduate student'
 if 'profile-page' in c:
  return 'Sidebar — '+('left' if 'profile-sidebar' in p['children'][0] else 'right with resources' if 'sidebar-resources' in ch else 'right')
 if 'image-text-row' in c:
  return 'Media — '+('text / image' if '--reverse' in c else 'landscape' if '--landscape' in c else 'wide image' if '--wide' in c else 'square image')
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
 if 'image-text-row' in c:
  # Exercise the production macro, including its responsive media behavior.
  opts=', reverse=true' if '--reverse' in c else ', landscape=true' if '--landscape' in c else ', wide=true' if '--wide' in c else ''
  return '{% call imageTextRow("/assets/grid-placeholder.svg", 600, 600, "Grid image placeholder"'+opts+') %}\n'+cell('Media row — text')+'{% endcall %}\n'
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
  return '<div class="row gy-4 gx-0 gx-md-5 profile-page">\n<div class="col-12 col-md-8 profile-biography">\n'+cell('Main content')+'</div>\n<div class="col-12 col-md-4 profile-sidebar sidebar-resources">\n'+buttons+'</div>\n</div>\n'
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
 body='{% from "layouts/content/image-text-row.njk" import imageTextRow %}\n'
 body+='<p>General page layouts from SSRI, PUBA, Ethnic Studies, Anthropology and Sociology. Resize this page or open it on another device to compare their columns and gaps.</p>\n'
 body+='<p>These examples use the existing shared styles. Names describe the current patterns; they are not the final standardized set. Responsive data tables and record directories are reviewed separately. Colored cells are placeholders. Seven cards reveal incomplete rows.</p>\n'
 body+='<p><strong>'+str(len(inventory['pages']))+' pages inventoried · '+str(len(patterns))+' layout signatures</strong></p>\n'
 groups=[('sidebars','Sidebars','Unequal columns, with supporting content on the left or right. Faculty bios use this same family.'),('equal-columns','Equal Columns','Equal-width rows with two, three or four columns, resource buttons and flowing lists.'),('cards-tiles','Cards & Tiles','Faculty and contact portrait grids, photo tiles and academic program tiles.'),('combined-layouts','Combined Layouts','Homepage arrangements and nested layouts such as paired advisors and sidebar button groups.')]
 body+='<div class="review-grid-tabs" role="tablist" aria-label="Layout patterns" hidden>\n'
 for key,label,intro in groups:
  body+='<button type="button" role="tab" id="tab-'+key+'" aria-controls="'+key+'" aria-selected="false" tabindex="-1">'+escape(label)+'</button>\n'
 body+='</div>\n'
 for key,label,intro in groups:
  body+='<section id="'+key+'" data-grid-panel aria-labelledby="tab-'+key+'">\n<h2>'+escape(label)+'</h2>\n<p>'+escape(intro)+' Common patterns appear first.</p>\n'
  for p in sorted(patterns,key=priority):
   if p['family']!=label:continue
   body+='<section class="review-grid-example" id="'+p['id']+'" aria-labelledby="'+p['id']+'-title">\n<h3 id="'+p['id']+'-title">'+escape(p['name'])+'</h3>\n'
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
