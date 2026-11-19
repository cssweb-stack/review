"""One shared, folder-based order for every unit's hero review."""
from collections import defaultdict
from pathlib import PurePosixPath
from urllib.parse import urlsplit
import re

FIXED = ('/', '/courses.html', '/contact.html', '/contact/', '/support.html')
POLICIES = ('/privacy.html', '/privacy/', '/policies-procedures.html', '/404.html')
LABELS = {'about': 'About', 'undergraduate': 'Undergraduate', 'graduate': 'Graduate', 'master-ma': 'MA', 'doctorate-phd': 'PhD', 'masters-mpa': 'MPA', 'faculty': 'Faculty Pages', 'news': 'News', 'bam': 'BAM', 'support': 'Support', 'research': 'Research'}


def navigation_urls(items):
    for item in items:
        url = item.get('url', '')
        if url.startswith('/'):
            yield url
        yield from navigation_urls(item.get('children', []))


def group_heroes(rows, source_info, navigation, degrees, news_index, unit):
    order = list(dict.fromkeys(navigation_urls(navigation)))
    for family in degrees.values():
        order.extend(p['url'] for p in family.get('pages', []) if p['url'] not in order)
    rank = {url: i for i, url in enumerate(order)}
    groups = defaultdict(list)
    articles = []
    for row in rows:
        url = row[1]
        info = source_info[url]
        if info['news']:
            articles.append(row)
            continue
        if url in FIXED:
            label = 'Fixed Pages'
        elif url in POLICIES:
            label = 'Privacy, Policies & 404'
        elif info['profile']:
            label = 'Faculty Bio Pages'
        elif url.startswith('/faculty/') or url in ('/faculty.html', '/directory.html', '/directory/', '/associated-faculty.html'):
            label = 'Faculty Pages'
        else:
            folders = PurePosixPath(info['source']).parts[:-1]
            label = ' / '.join(LABELS.get(part, part.replace('-', ' ').title()) for part in folders) if folders else 'Main Pages'
        groups[label].append(row)
    notes = {}
    if articles:
        articles.sort(key=lambda row: (-int(re.sub(r'\D', '', source_info[row[1]]['published'])[:8] or '0'), row[1]))
        sample = articles[0]
        groups['News Article Hero'] = [sample]
        index_row = next((row for row in rows if row[1] == news_index), None)
        def image_key(row):
            return re.sub(r'^/'+re.escape(unit)+r'(?=/media/)', '', urlsplit(row[2] or '').path)
        mismatches = [row for row in articles if not index_row or not image_key(row) or image_key(row) != image_key(index_row)]
        notes['News Article Hero'] = {'total': len(articles), 'sample': sample[1], 'index': news_index, 'mismatches': mismatches}
        # Exceptions must remain visible; never hide a mismatched article in the sample.
        if mismatches:
            groups['News Article Exceptions'] = [row for row in mismatches if row[1] != sample[1]]
    def group_order(label):
        first = label.split(' / ')[0]
        return ({'Fixed Pages': 0, 'Main Pages': 1, 'About': 2, 'Undergraduate': 3, 'Graduate': 4, 'News': 6, 'News Article Hero': 6, 'News Article Exceptions': 6, 'Faculty Pages': 7, 'Faculty Bio Pages': 8, 'Privacy, Policies & 404': 9}.get(first, 5), label)
    sections = []
    for label in sorted(groups, key=group_order):
        selected = groups[label]
        if not selected:
            continue
        if label == 'Fixed Pages':
            selected.sort(key=lambda row: FIXED.index(row[1]))
        elif label == 'Faculty Pages':
            selected.sort(key=lambda row: (row[1] not in ('/faculty/', '/faculty.html', '/directory/', '/directory.html'), rank.get(row[1], 9999), row[0].casefold()))
        elif label == 'Privacy, Policies & 404':
            selected.sort(key=lambda row: POLICIES.index(row[1]))
        else:
            selected.sort(key=lambda row: (PurePosixPath(source_info[row[1]]['source']).name != 'index.html', rank.get(row[1], 9999), row[0].casefold()))
        sections.append((label, selected, 2))
    return sections, notes


def duplicate_hero_urls(sections, unit):
    """Flag replaceable pages; fixed pages can cause a collision but stay protected."""
    from collections import Counter
    ignored = {'News Article Hero', 'News Article Exceptions'}
    protected = {'Fixed Pages', 'Faculty Pages', 'Faculty Bio Pages', 'Privacy, Policies & 404'}
    def image(row):
        return re.sub(r'^/'+re.escape(unit)+r'(?=/media/)', '', urlsplit(row[2] or '').path)
    candidates = [(group, row) for group, rows, _ in sections if group not in ignored for row in rows]
    counts = Counter(image(row) for _, row in candidates if image(row))
    return {row[1] for group, row in candidates if group not in protected and image(row) and counts[image(row)] > 1}
