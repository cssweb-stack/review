"""Inventory rendered placeholders and Google document links on current source routes."""
from pathlib import Path
from html import escape, unescape
from html.parser import HTMLParser
from urllib.parse import urlsplit
import json
import re


class PageInventory(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.anchor = None
        self.placeholders = 0
        self.hero = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a':
            self.anchor = {'url': attrs.get('href', ''), 'text': []}
        if tag == 'img' and self.anchor and attrs.get('alt'):
            self.anchor['text'].append(attrs['alt'])
        if tag == 'img' and any('temp.jpg' in urlsplit(attrs.get(key, '')).path.lower() for key in ('src', 'srcset')):
            self.placeholders += 1
        if 'temp.jpg' in attrs.get('style', '').lower():
            self.placeholders += 1
        if tag == 'section' and 'page-hero' in attrs.get('class', '').split():
            self.hero = True

    def handle_endtag(self, tag):
        if tag == 'a' and self.anchor:
            host = (urlsplit(self.anchor['url']).hostname or '').lower()
            if host in ('drive.google.com', 'docs.google.com', 'forms.google.com', 'forms.gle'):
                self.links.append({'url': self.anchor['url'], 'label': re.sub(r'\s+', ' ', ''.join(self.anchor['text'])).strip() or 'Google document'})
            self.anchor = None

    def handle_data(self, text):
        if self.anchor:
            self.anchor['text'].append(text)


def inventory(work, shared):
    units = json.loads((shared / 'data/common/review-units.json').read_text())['current']
    labels = json.loads((shared / 'data/common/title-standards.json').read_text())['units']
    results = {}
    for unit in units:
        pages = []
        for source in sorted((work / unit / 'src').rglob('*.html')):
            match = re.search(r'^permalink:\s*["\']?([^"\'\n]+)', source.read_text(), re.M)
            if not match:
                continue
            route = match[1].strip()
            built = work / unit / '_site' / (route.lstrip('/') + ('index.html' if route.endswith('/') else ''))
            if not built.is_file():
                raise RuntimeError(f'Build required for inventory: {unit}{route}')
            rendered = built.read_text()
            parser = PageInventory()
            parser.feed(rendered)
            heading = re.search(r'<h1\b[^>]*>(.*?)</h1>', rendered, re.S)
            name = unescape(re.sub(r'<[^>]*>', '', heading[1])).strip() if heading else route
            links = {item['url']: item for item in parser.links}
            pages.append({'route': route, 'url': f'https://cssweb-stack.github.io/{unit}{route}', 'name': name, 'placeholders': parser.placeholders, 'links': list(links.values()), 'hero': parser.hero})
        results[unit] = {'name': labels[unit], 'pages': pages}
    return results


def is_form(url):
    parsed = urlsplit(url)
    return parsed.hostname in ('forms.gle', 'forms.google.com') or parsed.path.startswith('/forms/')


def document_key(url):
    parsed = urlsplit(url)
    match = re.search(r'/(?:file|document|spreadsheets|presentation)/d/([^/]+)', parsed.path)
    if match:
        return match[1]
    return parsed.netloc + parsed.path


def classify_document(document):
    labels = ' '.join(document['labels']).lower()
    # The source paragraph explicitly names both formats as the same Plan B form.
    if document['key'] in ('1hz83aZLFimpWJUUpkFujvi6L5tZq9rXZ', '174MRjFCO17hSahml_N2XIzA_KzOrPnPG'):
        return 'Likely Forms — Kuali Candidates', 'The source paragraph describes a form completed and signed for the final examination.'
    if re.search(r'rubric|schedule an appointment', labels):
        return 'Needs Review', 'May collect evaluations or appointment information; inspect the document before deciding.'
    if re.search(r'form|application|approval|annual progress report|post-candidacy|synopsis|committee|evaluation sheet|check-in|coursework completion', labels):
        return 'Likely Forms — Kuali Candidates', 'The link wording or source section indicates an application, reporting, approval or completion form.'
    return 'Other Documents', 'Appears to be reference material, a schedule, spreadsheet, syllabus or CV.'


def unit_documents(unit):
    documents = {}
    for p in unit['pages']:
        for link in p['links']:
            if is_form(link['url']):
                continue
            key = document_key(link['url'])
            doc = documents.setdefault(key, {'key': key, 'url': link['url'], 'labels': [], 'pages': {}})
            if link['label'] not in doc['labels']:
                doc['labels'].append(link['label'])
            doc['pages'][p['url']] = p['name']
    return list(documents.values())


def render_document(document):
    category, reason = classify_document(document)
    label = document['labels'][0]
    if document['key'] == '1hz83aZLFimpWJUUpkFujvi6L5tZq9rXZ':
        label = 'MA Plan B Final Examination and Approval of Three Papers (Word)'
    elif document['key'] == '174MRjFCO17hSahml_N2XIzA_KzOrPnPG':
        label = 'MA Plan B Final Examination and Approval of Three Papers (fillable PDF)'
    body = '<li><a href="'+escape(document['url'], quote=True)+'">'+escape(label)+'</a><br>'+escape(category)+' — '+escape(reason)+'<br>'+escape(document['url'])
    pages = document['pages']
    links = '<ul>\n'+''.join('<li><a href="'+escape(url, quote=True)+'">'+escape(name)+'</a></li>\n' for url,name in pages.items())+'</ul>\n'
    if len(pages) > 1:
        body += '<details><summary>Appears on '+str(len(pages))+' pages</summary>\n'+links+'</details>\n'
    else:
        body += links
    return body+'</li>\n'


def build_asset_link_pages(out, page, work, shared):
    results = inventory(work, shared)
    files = {link['url'] for unit in results.values() for p in unit['pages'] for link in p['links'] if not is_form(link['url'])}
    file_pages = sum(any(not is_form(link['url']) for link in p['links']) for unit in results.values() for p in unit['pages'])
    placeholder_pages = sum(bool(p['placeholders']) for unit in results.values() for p in unit['pages'])
    drive = f'<p>{len(files)} distinct Google Drive/document links across {file_pages} pages. Each document appears once per unit. Repeated documents are grouped first, with expandable source-page lists. Likely forms are candidates for Kuali conversion; classifications are inferred from link wording and page context, not a file-content or accessibility audit. A Drive URL alone does not establish file type. Google Forms are listed separately below.</p>\n'
    categories = {}
    for unit in results.values():
        for document in unit_documents(unit):
            category = classify_document(document)[0]
            categories[category] = categories.get(category, 0) + 1
    drive += '<p>'+str(categories.get('Likely Forms — Kuali Candidates', 0))+' likely form links; '+str(categories.get('Needs Review', 0))+' uncertain items; '+str(categories.get('Other Documents', 0))+' other documents. Counts describe distinct file links, not necessarily distinct processes; Word and PDF versions of the same form are identified together by name.</p>\n'
    drive += '<ul>\n' + ''.join('<li><a href="#'+key+'">'+escape(unit['name'])+'</a></li>\n' for key,unit in results.items()) + '<li><a href="#google-forms">Google Forms</a></li>\n</ul>\n'
    placeholders = f'<p>{placeholder_pages} pages display the shared temp.jpg placeholder. Each page is listed once, with its number of placeholder occurrences.</p>\n'
    forms = {}
    for key, unit in results.items():
        drive += '<h2 id="' + key + '">' + escape(unit['name']) + '</h2>\n'
        placeholders += '<h2>' + escape(unit['name']) + '</h2>\n'
        documents = unit_documents(unit)
        repeated = [doc for doc in documents if len(doc['pages']) > 1]
        if repeated:
            drive += '<h3>Repeated Documents — Listed Once</h3>\n<ul>\n'+''.join(render_document(doc) for doc in repeated)+'</ul>\n'
        for category in ('Likely Forms — Kuali Candidates', 'Needs Review', 'Other Documents'):
            selected = [doc for doc in documents if len(doc['pages']) == 1 and classify_document(doc)[0] == category]
            if selected:
                drive += '<h3>'+escape(category)+'</h3>\n<ul>\n'+''.join(render_document(doc) for doc in selected)+'</ul>\n'
        if not documents:
            drive += '<p>No Google Drive/document links found.</p>\n'
        found_placeholder = False
        for p in unit['pages']:
            source_link = '<a href="' + escape(p['url'], quote=True) + '">' + escape(p['name']) + '</a>'
            if p['placeholders']:
                found_placeholder = True
                placeholders += '<p>' + source_link + ' — ' + str(p['placeholders']) + ' placeholder(s)<br>' + escape(p['url']) + '</p>\n'
            for link in p['links']:
                if is_form(link['url']):
                    form = forms.setdefault(link['url'], {'label': link['label'], 'units': {}})
                    form['units'].setdefault(key, []).append(p)
        if not found_placeholder:
            placeholders += '<p>No temp.jpg placeholders found.</p>\n'
    drive += '<h2 id="google-forms">Google Forms</h2>\n<p>Listed separately from files and documents; these are not identified as PDFs. Shared language-assistance forms appear throughout the sites.</p>\n'
    for url, form in forms.items():
        drive += '<h3><a href="'+escape(url, quote=True)+'">'+escape(form['label'])+'</a></h3>\n<p>'+escape(url)+'</p>\n<ul>\n'
        for key, pages in form['units'].items():
            if len(pages) == len(results[key]['pages']):
                drive += '<li>'+escape(results[key]['name'])+' — shared across all '+str(len(pages))+' pages; <a href="https://cssweb-stack.github.io/'+key+'/">homepage example</a></li>\n'
            else:
                for p in pages:
                    drive += '<li>'+escape(results[key]['name'])+' — <a href="'+escape(p['url'], quote=True)+'">'+escape(p['name'])+'</a></li>\n'
        drive += '</ul>\n'
    (out / 'google-drive-links.html').write_text(page('Google Drive Links', drive))
    (out / 'placeholder-images.html').write_text(page('Placeholder Images', placeholders))
    print(f'Inventories: {placeholder_pages} placeholder pages; {len(files)} distinct Google Drive/document links on {file_pages} pages; {len(forms)} Google Forms.')
