"""Check that Pages receives static HTML, current data, and existing local assets."""
import json
import os
from pathlib import Path
import re
import sys
root = Path(sys.argv[1])
page = root / 'index.html'
assert page.exists(), 'Missing static index.html'
text = page.read_text()
assert 'Discovery Radar' in text or 'discovery' in text, 'Missing product HTML'
assert 'Latest discoveries' in text, 'Main feed was not prerendered'
feed = json.loads((root / 'data/feed.json').read_text())
assert feed['items'], 'Empty research feed'
assert len({x['id'] for x in feed['items']}) == len(feed['items']), 'Duplicate item IDs'
for item in feed['items']:
    assert item['url'].startswith(('https://', 'http://')), 'Unsafe item URL'
    assert item['subjects'] and item['methods'], 'Missing topic tags'
    assert '_text' not in item, 'Internal source text must not be published'
base = os.environ.get('PAGES_BASE_PATH', '')
for ref in re.findall(r'(?:src|href)="([^"]+)"', text):
    for folder in ('assets', '_next'):
        marker = f'/{folder}/'
        if marker in ref:
            if base:
                assert ref.startswith(base + '/'), f'Incorrect project URL: {ref}'
            asset = ref.split(marker, 1)[1].split('?', 1)[0]
            assert (root / folder / asset).exists(), f'Missing asset {asset}'
print(f'Static export verified: {len(feed["items"])} unique items, HTML and assets present.')
