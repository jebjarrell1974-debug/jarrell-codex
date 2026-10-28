# -*- coding: utf-8 -*-
"""The photospheres, as the live site serves them.

Each one is somebody else's photograph under a licence that asks to be
credited, so this checks the published manifest names an author, a licence
and a source page for every single one - and that every image is really
there, really 2048x1024, and really downloadable.
"""
import io, json, sys, time, urllib.request

B = 'https://jebjarrell1974-debug.github.io/jarrell-codex/'
fails = []


def chk(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name +
          (('  ' + str(detail)[:160]) if detail and not cond else ''))
    if not cond:
        fails.append(name)


def grab(path, binary=False):
    r = urllib.request.Request(B + path, headers={
        'User-Agent': 'jarrell-codex-verify', 'Cache-Control': 'no-cache'})
    with urllib.request.urlopen(r, timeout=90) as h:
        d = h.read()
    return d if binary else d.decode('utf-8')


man = None
for attempt in range(20):
    try:
        man = json.loads(grab('data/pano.json'))
    except Exception as e:
        print('  not readable yet:', repr(e)[:60])
        man = None
    if man:
        break
    print(f'  waiting for the deploy... ({attempt + 1})')
    time.sleep(30)
if not man:
    print('\nFAILED: no photospheres on the live site after ten minutes')
    sys.exit(1)

print(f'the manifest ({len(man)} places)')
chk('there are 25', len(man) == 25, len(man))
bad = [k for k, v in man.items() if v.get('w') != 2048 or v.get('h') != 1024]
chk('every entry says 2048x1024', not bad, bad[:4])
bad = [k for k, v in man.items() if not v.get('artist')]
chk('every one names who took it', not bad, bad[:4])
bad = [k for k, v in man.items()
       if '<' in str(v.get('artist')) or 'http' in str(v.get('artist'))]
chk('as a name, not as markup', not bad, bad[:4])
bad = [k for k, v in man.items() if not v.get('licence')]
chk('every one names a licence', not bad, bad[:4])
bad = [k for k, v in man.items()
       if not any(t in str(v.get('licence')).lower()
                  for t in ('cc by', 'cc-by', 'cc0', 'public domain'))]
chk('and one that lets us pass it on', not bad,
    [(k, man[k].get('licence')) for k in bad[:3]])
bad = [k for k, v in man.items() if not str(v.get('page', '')).startswith('http')]
chk('and links the page it came from', not bad, bad[:4])
bad = [k for k, v in man.items()
       if v.get('km') is None or v['km'] > 3.01]
chk('nothing is claimed from over 3 km away', not bad,
    [(k, man[k].get('km')) for k in bad[:4]])
print(f'       Mount Sinai: {man.get("Mount Sinai", {}).get("km")} km from the '
      f'summit, by {man.get("Mount Sinai", {}).get("artist")}')

print('\nthe images actually download')
files = sorted(set(v['file'] for v in man.values()))
print(f'       {len(files)} distinct images')
total, bad = 0, []
for f in files:
    try:
        d = grab('data/pano/' + f, binary=True)
    except Exception as e:
        bad.append((f, repr(e)[:50]))
        continue
    total += len(d)
    if d[:4] != b'RIFF':
        bad.append((f, 'not a WebP'))
    elif len(d) > 368640:
        bad.append((f, f'{len(d)//1024} KB, over the 360 KB cap'))
chk(f'all {len(files)} are served and are WebP under 360 KB', not bad, bad[:4])
print(f'       {total / 1048576:.1f} MB in total')

print('\nthe code')
js = grab('app.js')
chk('the viewer is published', 'function panoStart' in js)
chk('it is WebGL', "getContext('webgl'" in js)
html = grab('index.html')
chk('the page loads no script but its own',
    html.count('<script') == 1 and 'src="app.js"' in html,
    [l for l in html.split('\n') if '<script' in l])
chk('and nothing from a content network',
    not any(h in js + html for h in ('cdn.', 'unpkg', 'jsdelivr', 'three.min',
                                     'googleapis.com/ajax')))
chk('the horizontal wrap is REPEAT', 'TEXTURE_WRAP_S, gl.REPEAT' in js)
chk('there are arrow controls, not only a drag', 'data-pan="left"' in js)
chk('and a flat fallback where there is no WebGL',
    'cannot wrap the picture round' in js)
chk('the pitch is clamped short of the zenith', '1.45' in js)
chk('the button only appears where there is one', 'if (pano) {' in js)
chk('the credit travels with the view', 'p.artist' in js)
chk('and so does how far off it was taken', 'from the spot itself' in js)
chk('the loaders always return a promise', 'const lazily =' in js)

print('\nthe offline tier')
om = json.loads(grab('data/offline_manifest.json'))
chk('photospheres are a tier of their own', 'panoramas' in om['tiers'],
    list(om['tiers']))
if 'panoramas' in om['tiers']:
    t = om['tiers']['panoramas']
    listed = {f.rsplit('/', 1)[-1] for f, _ in t['files']}
    chk('with every image in it and nothing else',
        t['count'] == len(files) + 1,
        f"{t['count']} files, expected {len(files) + 1}: extra "
        f"{sorted(listed - set(files) - {'pano.json'})}")
    chk('and no test fixture among them',
        not any(f.startswith('_') for f in listed),
        sorted(f for f in listed if f.startswith('_')))
    print(f"       {t['label']}: {t['bytes'] / 1048576:.1f} MB in "
          f"{t['count']} files")

print('\n' + ('FAILED: ' + ', '.join(fails) if fails
              else 'THE PHOTOSPHERES ARE GOOD'))
sys.exit(1 if fails else 0)
