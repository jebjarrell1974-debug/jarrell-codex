# -*- coding: utf-8 -*-
"""Attribution, as the live site actually serves it.

Fourteen photographs went out under CC BY, CC BY-SA or GPL with no
photographer named. The fix is only real if the published manifest carries
the credits and the published page prints them, so check both there rather
than here.
"""
import json, sys, time, urllib.request

B = 'https://jebjarrell1974-debug.github.io/jarrell-codex/'
fails = []


def chk(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name +
          (('  ' + str(detail)[:170]) if detail and not cond else ''))
    if not cond:
        fails.append(name)


def grab(path):
    r = urllib.request.Request(B + path, headers={
        'User-Agent': 'jarrell-codex-verify', 'Cache-Control': 'no-cache'})
    with urllib.request.urlopen(r, timeout=60) as h:
        return h.read().decode('utf-8')


def txt(o, k):
    v = o.get(k)
    return v if isinstance(v, str) else ''


def public(o):
    lic = (txt(o, 'licence') + ' ' + txt(o, 'licurl')).lower()
    return 'publicdomain' in lic or 'public domain' in lic or 'cc0' in lic


# The fix may still be deploying.
man = None
for attempt in range(20):
    man = json.loads(grab('data/pix_manifest.json'))
    owed = [k for k, o in man.items() if not public(o) and not txt(o, 'artist')]
    if not owed:
        break
    print(f'  {len(owed)} still uncredited on the live site, waiting... '
          f'({attempt + 1})')
    time.sleep(30)

print('the published manifest')
chk('307 photographs', len(man) == 307, len(man))
owed = [k for k, o in man.items() if not public(o) and not txt(o, 'artist')]
chk('none under an attribution licence lacks an author', not owed, owed[:6])
chk('every photograph names a licence',
    all(txt(o, 'licence') for o in man.values()),
    [k for k, o in man.items() if not txt(o, 'licence')][:4])
chk('every photograph links its source page',
    all(txt(o, 'page') for o in man.values()),
    [k for k, o in man.items() if not txt(o, 'page')][:4])
named = sum(1 for o in man.values() if txt(o, 'artist'))
print(f'       {named} of {len(man)} carry a named credit; '
      f'the rest are public domain')
# the ones that had to be fixed
for k in ('Heracleopolis Magna', 'Arabia 2', 'Bethlehem 2', 'Puteoli'):
    chk(f'{k} is credited', bool(txt(man.get(k, {}), 'artist')),
        man.get(k))

print('\nthe published page prints them')
js = grab('app.js')
chk('the photograph caption uses the artist field', 'credit' in js)
chk('and falls back to Wikimedia Commons rather than to nothing',
    'Wikimedia Commons' in js)
chk('the about list credits Wikimedia Commons and Wikidata',
    'Wikimedia Commons and Wikidata' in js)
chk('and credits LibriVox for the readings', 'LibriVox, via archive.org' in js)
chk('and Dore for the engravings',
    'Gustave Dor' in js and '1866' in js)

print('\n' + ('FAILED: ' + ', '.join(fails) if fails
              else 'ATTRIBUTION IS GOOD'))
sys.exit(1 if fails else 0)
