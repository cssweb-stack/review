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


def build_asset_link_pages(out, page, work, shared):
    results = inventory(work, shared)
    files = {link['url'] for unit in results.values() for p in unit['pages'] for link in p['links'] if not is_form(link['url'])}
    file_pages = sum(any(not is_form(link['url']) for link in p['links']) for unit in results.values() for p in unit['pages'])
    placeholder_pages = sum(bool(p['placeholders']) for unit in results.values() for p in unit['pages'])
    drive = f'<p>{len(files)} distinct Google Drive/document links across {file_pages} pages. Grouped by unit and the page containing the link. A Drive URL alone does not establish that its file is a PDF or that it is accessible. Google Forms are listed separately below.</p>\n'
    drive += '<ul>\n' + ''.join('<li><a href="#'+key+'">'+escape(unit['name'])+'</a></li>\n' for key,unit in results.items()) + '<li><a href="#google-forms">Google Forms</a></li>\n</ul>\n'
    placeholders = f'<p>{placeholder_pages} pages display the shared temp.jpg placeholder. Each page is listed once, with its number of placeholder occurrences.</p>\n'
    forms = {}
    for key, unit in results.items():
        drive += '<h2 id="' + key + '">' + escape(unit['name']) + '</h2>\n'
        placeholders += '<h2>' + escape(unit['name']) + '</h2>\n'
        found_drive = False
        found_placeholder = False
        for p in unit['pages']:
            source_link = '<a href="' + escape(p['url'], quote=True) + '">' + escape(p['name']) + '</a>'
            if p['placeholders']:
                found_placeholder = True
                placeholders += '<p>' + source_link + ' — ' + str(p['placeholders']) + ' placeholder(s)<br>' + escape(p['url']) + '</p>\n'
            document_links = [link for link in p['links'] if not is_form(link['url'])]
            if document_links:
                found_drive = True
                drive += '<h3>' + source_link + '</h3>\n<ul>\n'
                for link in document_links:
                    drive += '<li><a href="' + escape(link['url'], quote=True) + '">' + escape(link['label']) + '</a><br>' + escape(link['url']) + '</li>\n'
                drive += '</ul>\n'
            for link in p['links']:
                if is_form(link['url']):
                    form = forms.setdefault(link['url'], {'label': link['label'], 'units': {}})
                    form['units'].setdefault(key, []).append(p)
        if not found_drive:
            drive += '<p>No Google Drive/document links found.</p>\n'
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
