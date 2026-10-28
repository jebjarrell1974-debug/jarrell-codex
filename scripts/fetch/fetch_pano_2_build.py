# -*- coding: utf-8 -*-
"""Phase two: fetch the chosen photospheres and make them phone-sized.

The originals run to 12288x6144 and twenty-odd megabytes. Nobody is
downloading that to look at a hillside, so Commons is asked for a
server-side 2048-wide thumbnail instead of the full file - which also
means the bandwidth spent is theirs by design rather than ours by
accident.

2048x1024 exactly: a power of two in both directions, so the viewer's
horizontal wrap is the hardware's REPEAT and needs no mipmap tricks, and
2:1 because that is what equirectangular means. Anything that does not
come back at that ratio is dropped rather than squashed into it.
"""
import hashlib, io, json, os, sys, time, urllib.parse, urllib.request
from PIL import Image

API = 'https://commons.wikimedia.org/w/api.php'
UA = {'User-Agent': 'jarrell-codex/1.0 (place photospheres; '
                    'https://github.com/jebjarrell1974-debug/jarrell-codex)'}
CAND = r'C:\Android\work\pano_candidates.json'
OUTDIR = r'C:\Android\work\panoout'
MAN = r'C:\Android\work\pano.json'
W, H = 2048, 1024
CAP = 360 * 1024          # the photographs are capped at 300 KB; allow a little more


def ask(params, tries=4):
    last = None
    for k in range(tries):
        try:
            q = urllib.parse.urlencode(params)
            r = urllib.request.Request(API + '?' + q, headers=UA)
            with urllib.request.urlopen(r, timeout=90) as h:
                d = json.load(h)
            if 'error' in d:
                raise RuntimeError(str(d['error'])[:120])
            return d
        except Exception as e:
            last = e
            time.sleep(3 + 5 * k)
    raise RuntimeError(f'{type(last).__name__}: {str(last)[:100]}')


def thumb_url(title, width=W):
    d = ask({'action': 'query', 'format': 'json', 'prop': 'imageinfo',
             'iiprop': 'url|size', 'iiurlwidth': width, 'titles': title})
    for pg in (d.get('query', {}).get('pages', {}) or {}).values():
        ii = (pg.get('imageinfo') or [{}])[0]
        return ii.get('thumburl') or ii.get('url')
    return None


def grab(url):
    r = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(r, timeout=180) as h:
        return h.read()


def slug(name):
    s = ''.join(c.lower() if c.isalnum() else '-' for c in name)
    while '--' in s:
        s = s.replace('--', '-')
    return s.strip('-') or 'place'


def page_url(title):
    return 'https://commons.wikimedia.org/wiki/' + urllib.parse.quote(
        title.replace(' ', '_'))


cand = json.load(io.open(CAND, encoding='utf-8'))
want = {n: v['best'][0] for n, v in cand.items()
        if v.get('found') and v.get('best')}
print(f'places searched        : {len(cand)}')
print(f'places with a sphere   : {len(want)}')

os.makedirs(OUTDIR, exist_ok=True)
man = {}
if os.path.exists(MAN):
    man = json.load(io.open(MAN, encoding='utf-8'))
    print(f'already built          : {len(man)}  (resuming)')

# Several places can land on the same Mapillary frame. Store it once.
by_title = {}
for name, m in man.items():
    by_title[m.get('title', '')] = m['file']

todo = [n for n in sorted(want) if n not in man]
print(f'left to fetch          : {len(todo)}\n')

dropped, total_bytes = [], 0
for i, name in enumerate(todo, 1):
    c = want[name]
    title = c['title']
    try:
        if title in by_title:
            file = by_title[title]
        else:
            url = thumb_url(title)
            if not url:
                dropped.append((name, 'no url'))
                continue
            raw = grab(url)
            img = Image.open(io.BytesIO(raw)).convert('RGB')
            if not (1.95 <= img.width / img.height <= 2.05):
                dropped.append((name, f'came back {img.width}x{img.height}'))
                continue
            img = img.resize((W, H), Image.LANCZOS)
            file = slug(name) + '.webp'
            path = os.path.join(OUTDIR, file)
            # Walk the quality down until it fits, rather than picking a
            # number and hoping.
            for q in (74, 68, 62, 56, 50, 44):
                img.save(path, 'WEBP', quality=q, method=5)
                if os.path.getsize(path) <= CAP:
                    break
            by_title[title] = file
            total_bytes += os.path.getsize(path)
            time.sleep(0.5)
        man[name] = {
            'file': file, 'w': W, 'h': H, 'km': c.get('km'),
            'licence': c.get('licence') or 'CC BY-SA 4.0',
            'artist': (c.get('artist') or '').strip(),
            'taken': (c.get('taken') or '')[:10],
            'page': page_url(title),
            'title': title,
        }
        size = os.path.getsize(os.path.join(OUTDIR, file)) / 1024
        print(f'  {name[:26]:<28} {size:>5.0f} KB  {c.get("km")} km away')
    except Exception as e:
        dropped.append((name, f'{type(e).__name__}: {str(e)[:60]}'))
        print(f'  {name[:26]:<28} FAILED {type(e).__name__}')
    if i % 10 == 0:
        io.open(MAN, 'w', encoding='utf-8').write(
            json.dumps(man, ensure_ascii=False))
        print(f'  --- {i}/{len(todo)}', flush=True)

io.open(MAN, 'w', encoding='utf-8').write(json.dumps(man, ensure_ascii=False))

files = sorted(set(m['file'] for m in man.values()))
onbytes = sum(os.path.getsize(os.path.join(OUTDIR, f)) for f in files)
print(f'\nplaces with a photosphere : {len(man)}')
print(f'distinct images           : {len(files)}')
print(f'on disk                   : {onbytes / 1048576:.1f} MB')
print(f'largest                   : '
      f'{max(os.path.getsize(os.path.join(OUTDIR, f)) for f in files) / 1024:.0f} KB')
lic = {}
noart = []
for n, m in man.items():
    lic[m['licence']] = lic.get(m['licence'], 0) + 1
    if not m['artist']:
        noart.append(n)
print(f'licences                  : {dict(sorted(lic.items(), key=lambda kv: -kv[1]))}')
print(f'without a named author    : {len(noart)}')
if noart:
    print('   ', noart[:8])
if dropped:
    print(f'\ndropped {len(dropped)}:')
    for n, why in dropped[:15]:
        print(f'   {n[:26]:<28} {why}')
print(f'\nmanifest {MAN}, images {OUTDIR}')
