# -*- coding: utf-8 -*-
"""Do I believe the zeros?

Golgotha came back with 18 panoramas and Gethsemane with 0, and they are
900 metres apart. Inside an 8 km radius those two should return almost the
same set, so one of those numbers is wrong. Asking each three times
settles whether the zeros are facts about Commons or hiccups in my query -
and I am not quoting a coverage figure to anyone until it does.
"""
import json, time, urllib.parse, urllib.request

API = 'https://commons.wikimedia.org/w/api.php'
UA = {'User-Agent': 'jarrell-codex/1.0 (coverage survey; '
                    'https://github.com/jebjarrell1974-debug/jarrell-codex)'}
CAT = '360° panoramas with equirectangular projection'

SUSPECT = {
    'Golgotha': (31.778444, 35.22975),
    'Gethsemane': (31.779419, 35.239425),
    'Mount of Olives': (31.777946, 35.245686),
    'Jerusalem': (31.776667, 35.234167),
}


def count(lat, lon, km):
    q = urllib.parse.urlencode({
        'action': 'query', 'format': 'json', 'list': 'search',
        'srnamespace': 6, 'srlimit': 50,
        'srsearch': f'incategory:"{CAT}" nearcoord:{km}km,{lat},{lon}'})
    r = urllib.request.Request(API + '?' + q, headers=UA)
    with urllib.request.urlopen(r, timeout=60) as h:
        d = json.load(h)
    if 'error' in d:
        return 'ERROR ' + str(d['error'])[:70]
    s = d.get('query', {}).get('search', [])
    hits = d.get('query', {}).get('searchinfo', {}).get('totalhits')
    return f'{len(s)} returned, totalhits {hits}'


for name, (lat, lon) in SUSPECT.items():
    print(name)
    for km in (2, 8, 20):
        for attempt in range(3):
            print(f'   {km:>2} km, try {attempt + 1}: {count(lat, lon, km)}')
            time.sleep(1.2)
