# -*- coding: utf-8 -*-
"""Fourth pass, and the first one that asks the right question.

The earlier passes took the 50 geotagged files nearest a point and looked
for panoramas among them. That undercounts badly: near Jerusalem the
nearest 50 files are photographs of walls and doorways, and the panoramas
are somewhere down the list. It said 0 for Jerusalem, which is a statement
about my query and not about Commons.

Commons' search can intersect a category with a radius directly -
`incategory:"..." nearcoord:5km,lat,lon` - which is the actual question:
is there a 360 of this place, anywhere in the set of 360s? That is what
this asks, across every category Commons uses to mark one.
"""
import io, json, time, urllib.parse, urllib.request

API = 'https://commons.wikimedia.org/w/api.php'
UA = {'User-Agent': 'jarrell-codex/1.0 (coverage survey; '
                    'https://github.com/jebjarrell1974-debug/jarrell-codex)'}

CATS = [
    '360\u00b0 panoramas with equirectangular projection',
    '360\u00b0 panoramas',
    '360\u00b0 panoramic photographs',
    'Cubemap representation of 360\u00b0 panorama',
]

PLACES = {
    'Mount Sinai': (28.539722, 33.973333),
    'Jerusalem': (31.776667, 35.234167),
    'Nazareth': (32.70214, 35.29769),
    'Sea of Galilee': (32.818906, 35.590033),
    'Capernaum': (32.881111, 35.575),
    'Golgotha': (31.778444, 35.22975),
    'Gethsemane': (31.779419, 35.239425),
    'Mount of Olives': (31.777946, 35.245686),
    'Jordan': (31.761389, 35.558333),
    'Nineveh': (36.3594, 43.1528),
    'Damascus': (33.511112, 36.30639),
    'Caesarea': (32.5, 34.891667),
    'Athens': (37.971851, 23.726738),
    'Rome': (41.8922, 12.4852),
    'Patmos': (37.325, 26.541667),
    'Ephesus': (37.939125, 27.3407),
    'Corinth': (37.905785, 22.878741),
    'Bethel': (31.9303, 35.2217),
    'Hebron': (31.5333, 35.0956),
    'Jaffa': (32.0533, 34.7522),
    'Shiloh': (32.0556, 35.2897),
    'Megiddo': (32.5847, 35.1836),
    'Masada': (31.3156, 35.3539),
    'Petra': (30.3286, 35.4419),
    'Mount Carmel': (32.7333, 35.05),
    'Mount Tabor': (32.6869, 35.3906),
    'Jezreel': (32.5572, 35.3281),
    'Beersheba': (31.2447, 34.8378),
    'Samaria': (32.2764, 35.1956),
    'Shechem': (32.2139, 35.2806),
}


class ApiError(Exception):
    pass


def ask(params, tries=4):
    last = None
    for k in range(tries):
        try:
            q = urllib.parse.urlencode(params)
            r = urllib.request.Request(API + '?' + q, headers=UA)
            with urllib.request.urlopen(r, timeout=60) as h:
                d = json.load(h)
            if 'error' in d:
                raise ApiError(str(d['error'])[:150])
            return d
        except Exception as e:
            last = e
            time.sleep(2 + 4 * k)
    raise ApiError(f'{type(last).__name__}: {str(last)[:110]}')


def panos(lat, lon, km=8):
    """Every file in any 360 category within km of the point."""
    hits = {}
    for cat in CATS:
        d = ask({'action': 'query', 'format': 'json', 'list': 'search',
                 'srnamespace': 6, 'srlimit': 50,
                 'srsearch': f'incategory:"{cat}" '
                             f'nearcoord:{km}km,{lat},{lon}'})
        for r in d.get('query', {}).get('search', []):
            hits[r['title']] = cat
        time.sleep(0.4)
    return hits


def details(titles):
    out = {}
    for i in range(0, len(titles), 25):
        d = ask({'action': 'query', 'format': 'json', 'prop': 'imageinfo',
                 'iiprop': 'size|url|extmetadata',
                 'iiextmetadatafilter': 'LicenseShortName|Artist',
                 'titles': '|'.join(titles[i:i + 25])})
        for pg in (d.get('query', {}).get('pages', {}) or {}).values():
            ii = (pg.get('imageinfo') or [{}])[0]
            em = ii.get('extmetadata') or {}
            out[pg.get('title', '')] = {
                'w': ii.get('width', 0), 'h': ii.get('height', 0),
                'url': ii.get('url', ''),
                'licence': (em.get('LicenseShortName') or {}).get('value', ''),
                'artist': (em.get('Artist') or {}).get('value', '')[:80],
            }
        time.sleep(0.4)
    return out


report, failed, total = {}, [], 0
print(f'{"place":<17}{"360s within 8 km":>18}  {"2:1 and usable":>15}')
for name, (lat, lon) in PLACES.items():
    try:
        hits = panos(lat, lon)
        meta = details(list(hits)) if hits else {}
    except ApiError as e:
        print(f'{name:<17}  COULD NOT TELL - {e}')
        failed.append(name)
        continue
    # An equirectangular 360 is twice as wide as it is tall. That is the
    # test for whether a viewer can actually wrap it round the reader.
    usable = [t for t, m in meta.items()
              if m['w'] and m['h'] and 1.9 <= m['w'] / m['h'] <= 2.1
              and m['w'] >= 2000]
    total += len(usable)
    print(f'{name:<17}{len(hits):>18}  {len(usable):>15}')
    report[name] = {
        'in_a_360_category': len(hits),
        'usable': [{'title': t, 'w': meta[t]['w'], 'h': meta[t]['h'],
                    'licence': meta[t]['licence'], 'artist': meta[t]['artist'],
                    'url': meta[t]['url']}
                   for t in usable],
    }
    time.sleep(0.5)

io.open(r'C:\Android\work\pano_survey.json', 'w', encoding='utf-8').write(
    json.dumps({'places': report, 'could_not_tell': failed},
               ensure_ascii=False, indent=1))
have = [k for k, v in report.items() if v['usable']]
print(f'\nasked about {len(PLACES)} places')
print(f'  with at least one usable 360 : {len(have)}')
print(f'  with none                    : {len(report) - len(have)}')
print(f'  could not tell               : {len(failed)}')
print(f'  usable panoramas in total    : {total}')
lic = {}
for v in report.values():
    for u in v['usable']:
        lic[u['licence']] = lic.get(u['licence'], 0) + 1
print('  licences:', dict(sorted(lic.items(), key=lambda kv: -kv[1])))
print('details in pano_survey.json')
