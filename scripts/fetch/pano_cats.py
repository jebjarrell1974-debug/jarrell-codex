# -*- coding: utf-8 -*-
"""Which category are the usable panoramas actually in?

The strict "equirectangular projection" category returned nothing near
Jerusalem, yet the union of four categories returned 21 files that are
plainly equirectangular - 5760x2880, exactly 2:1. So one of the looser
categories is where the Mapillary uploads live, and the fetcher needs to
query the right one rather than all four at 1,342 places.
"""
import json, time, urllib.parse, urllib.request

API = 'https://commons.wikimedia.org/w/api.php'
UA = {'User-Agent': 'jarrell-codex/1.0 (https://github.com/'
                    'jebjarrell1974-debug/jarrell-codex)'}

SAMPLE = [
    'File:Photo from Mapillary 2025-11-20 (1149317500248786).jpg',
    'File:Mapillary (htJKXKJVM6S44npqJWGnwF) (360ms) '
    '2021-05-08 10H24M48S000.jpg',
]


def ask(params):
    q = urllib.parse.urlencode(params)
    r = urllib.request.Request(API + '?' + q, headers=UA)
    with urllib.request.urlopen(r, timeout=60) as h:
        return json.load(h)


print('categories on two known-good panoramas')
d = ask({'action': 'query', 'format': 'json', 'prop': 'categories',
         'cllimit': 'max', 'titles': '|'.join(SAMPLE)})
for pg in (d.get('query', {}).get('pages', {}) or {}).values():
    print(' ', pg.get('title', '').encode('ascii', 'replace').decode()[:70])
    for c in (pg.get('categories') or []):
        print('      ', c['title'].encode('ascii', 'replace').decode())

# And how big each candidate category is, so the fetcher knows what it is
# drawing from.
print('\nhow many files in each category')
for cat in ('360° panoramas with equirectangular projection',
            '360° panoramas',
            '360° panoramic photographs',
            'Spherical panoramics',
            'Images from Mapillary'):
    d = ask({'action': 'query', 'format': 'json', 'list': 'categoryinfo',
             'titles': 'Category:' + cat})
    for pg in (d.get('query', {}).get('pages', {}) or {}).values():
        ci = pg.get('categoryinfo') or {}
        miss = 'missing' in pg
        print(f'  {cat[:52]:<54} '
              f'{"(no such category)" if miss else ci.get("files", 0)}')
    time.sleep(0.5)

# The one query the fetcher will actually use, tried on Jerusalem.
print('\nthe combined query, on Jerusalem')
for q in ('incategory:"360° panoramas"',
          'incategory:"360° panoramas with equirectangular projection"',
          'incategory:"360° panoramas"|"360° panoramas with '
          'equirectangular projection"'):
    d = ask({'action': 'query', 'format': 'json', 'list': 'search',
             'srnamespace': 6, 'srlimit': 5,
             'srsearch': f'{q} nearcoord:8km,31.776667,35.234167'})
    info = d.get('query', {}).get('searchinfo', {})
    print(f'  {q[:70]:<72} totalhits {info.get("totalhits")}')
    time.sleep(0.8)
