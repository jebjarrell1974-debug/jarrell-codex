# -*- coding: utf-8 -*-
"""Phase one: find a 360 photosphere for every place that has coordinates.

Two things were settled before writing this. The category is
"360 panoramas" - the Mapillary uploads live there, and the
"equirectangular projection" subcategory holds none of them. And the pipe
form of incategory returns nothing, so it is one category per query.

Search only. Nothing is downloaded here, because the searching is the slow
part and a crash during a download should not cost it. Phase two picks up
candidates.json and fetches.

Radius matters and is a judgement: a photosphere two kilometres from a
named hill is still a photosphere of that hill's surroundings, but one
eight kilometres away may be a different valley. 3 km, and the distance is
recorded per file so the viewer can say how far off it was taken.
"""
import io, json, math, os, sys, time, urllib.parse, urllib.request

API = 'https://commons.wikimedia.org/w/api.php'
UA = {'User-Agent': 'jarrell-codex/1.0 (place photospheres; '
                    'https://github.com/jebjarrell1974-debug/jarrell-codex)'}
CAT = '360\u00b0 panoramas'
PLACES = r'C:\Android\work\ghp3\data\place.json'
OUT = r'C:\Android\work\pano_candidates.json'
RADIUS_KM = 3


class ApiError(Exception):
    pass


def ask(params, tries=5):
    last = None
    for k in range(tries):
        try:
            q = urllib.parse.urlencode(params)
            r = urllib.request.Request(API + '?' + q, headers=UA)
            with urllib.request.urlopen(r, timeout=60) as h:
                d = json.load(h)
            if 'error' in d:
                raise ApiError(str(d['error'])[:120])
            return d
        except Exception as e:
            last = e
            time.sleep(3 + 5 * k)
    raise ApiError(f'{type(last).__name__}: {str(last)[:100]}')


def km_between(a_lat, a_lon, b_lat, b_lon):
    r = 6371.0
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp = p2 - p1
    dl = math.radians(b_lon - a_lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(h)))


def search(lat, lon):
    d = ask({'action': 'query', 'format': 'json', 'list': 'search',
             'srnamespace': 6, 'srlimit': 50,
             'srsearch': f'incategory:"{CAT}" '
                         f'nearcoord:{RADIUS_KM}km,{lat},{lon}'})
    return [r['title'] for r in d.get('query', {}).get('search', [])]


def details(titles):
    out = {}
    for i in range(0, len(titles), 25):
        d = ask({'action': 'query', 'format': 'json',
                 'prop': 'imageinfo|coordinates',
                 'iiprop': 'size|url|extmetadata',
                 'iiextmetadatafilter': 'LicenseShortName|Artist|DateTimeOriginal',
                 'titles': '|'.join(titles[i:i + 25])})
        for pg in (d.get('query', {}).get('pages', {}) or {}).values():
            ii = (pg.get('imageinfo') or [{}])[0]
            em = ii.get('extmetadata') or {}
            co = (pg.get('coordinates') or [{}])[0]
            out[pg.get('title', '')] = {
                'w': ii.get('width', 0), 'h': ii.get('height', 0),
                'url': ii.get('url', ''),
                'licence': (em.get('LicenseShortName') or {}).get('value', ''),
                'artist': (em.get('Artist') or {}).get('value', '')[:160],
                'taken': (em.get('DateTimeOriginal') or {}).get('value', '')[:40],
                'lat': co.get('lat'), 'lon': co.get('lon'),
            }
        time.sleep(0.4)
    return out


places = json.load(io.open(PLACES, encoding='utf-8'))
located = {n: (d['lat'], d['lon']) for n, d in places.items()
           if d.get('lat') is not None and d.get('lon') is not None}
print(f'places in the database : {len(places)}')
print(f'with coordinates       : {len(located)}')

# Resume: this takes half an hour and should survive being interrupted.
done = {}
if os.path.exists(OUT):
    done = json.load(io.open(OUT, encoding='utf-8'))
    print(f'already searched       : {len(done)}  (resuming)')

names = [n for n in sorted(located) if n not in done]
print(f'left to search         : {len(names)}\n')

for i, name in enumerate(names, 1):
    lat, lon = located[name]
    try:
        titles = search(lat, lon)
        meta = details(titles) if titles else {}
    except ApiError as e:
        # Recorded as a failure, never as "none found". The two are
        # different answers and the whole point of the earlier mess.
        done[name] = {'error': str(e)}
        print(f'  {name[:28]:<30} COULD NOT TELL  {str(e)[:50]}')
        continue
    good = []
    for t, m in meta.items():
        if not m['w'] or not m['h']:
            continue
        ratio = m['w'] / m['h']
        if not (1.95 <= ratio <= 2.05):
            continue              # not equirectangular; cannot be wrapped
        if m['w'] < 2048:
            continue              # too small to look around inside
        d_km = (km_between(lat, lon, m['lat'], m['lon'])
                if m['lat'] is not None else None)
        good.append({'title': t, 'w': m['w'], 'h': m['h'], 'url': m['url'],
                     'licence': m['licence'], 'artist': m['artist'],
                     'taken': m['taken'], 'km': round(d_km, 2)
                     if d_km is not None else None})
    # Nearest first, then largest. A photosphere taken at the place beats a
    # sharper one taken down the road.
    good.sort(key=lambda g: (g['km'] if g['km'] is not None else 99,
                             -g['w']))
    done[name] = {'found': len(good), 'best': good[:3]}
    if good:
        print(f'  {name[:28]:<30} {len(good):>3} found, nearest '
              f'{good[0]["km"]} km, {good[0]["w"]}x{good[0]["h"]}')
    if i % 25 == 0:
        io.open(OUT, 'w', encoding='utf-8').write(
            json.dumps(done, ensure_ascii=False))
        hits = sum(1 for v in done.values() if v.get('found'))
        print(f'  --- {i}/{len(names)} searched, {hits} places with a '
              f'photosphere so far', flush=True)
    time.sleep(0.7)

io.open(OUT, 'w', encoding='utf-8').write(json.dumps(done, ensure_ascii=False))
hits = [n for n, v in done.items() if v.get('found')]
errs = [n for n, v in done.items() if v.get('error')]
print(f'\nsearched            : {len(done)}')
print(f'with a photosphere  : {len(hits)}')
print(f'with none           : {len(done) - len(hits) - len(errs)}')
print(f'could not tell      : {len(errs)}')
lic = {}
for v in done.values():
    for b in v.get('best', []):
        lic[b['licence']] = lic.get(b['licence'], 0) + 1
print(f'licences            : {dict(sorted(lic.items(), key=lambda kv: -kv[1]))}')
print(f'written to {OUT}')
