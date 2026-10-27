# -*- coding: utf-8 -*-
"""Re-check only the failures, one at a time, with retries.

Twelve concurrent HEADs against archive.org produced twenty HTTP 500s,
which is the shape of rate limiting rather than of missing files - a file
that is not there returns 404. Serially, with a pause and three tries,
tells the two apart. A URL that still fails is a URL the player must not
point at.
"""
import json, sys, time, urllib.request

B = 'https://jebjarrell1974-debug.github.io/jarrell-codex/data/audio.json'

def head(u, tries=4):
    last = ''
    for k in range(tries):
        r = urllib.request.Request(u, method='HEAD',
                                   headers={'User-Agent': 'jarrell-codex-verify'})
        try:
            with urllib.request.urlopen(r, timeout=60) as h:
                return h.status, h.headers.get('content-type', ''), \
                       int(h.headers.get('content-length') or 0), k + 1
        except Exception as e:
            last = repr(e)[:70]
            time.sleep(2 + 3 * k)
    return 0, last, 0, tries

with urllib.request.urlopen(B, timeout=60) as h:
    ix = json.load(h)
urls = [f['u'] for f in ix['files']]

print(f'checking {len(urls)} readings one at a time')
dead, retried = [], []
for i, u in enumerate(urls, 1):
    st, ct, ln, tries = head(u)
    if st != 200:
        dead.append((st, ct, u))
        print(f'  DEAD  {st} {ct}  {u}')
    elif tries > 1:
        retried.append((tries, u))
    if i % 50 == 0:
        print(f'  ...{i}/{len(urls)}  ({len(dead)} dead, {len(retried)} needed a retry)')
    time.sleep(0.15)

print(f'\nreachable      : {len(urls) - len(dead)}/{len(urls)}')
print(f'needed a retry : {len(retried)}  (archive.org rate limiting, not a missing file)')
if dead:
    print(f'\nFAILED: {len(dead)} genuinely unreachable')
    for st, ct, u in dead:
        print('   ', st, ct, u)
    json.dump([u for _, _, u in dead], open('dead_audio.json', 'w'))
    sys.exit(1)
print('\nEVERY READING IS REACHABLE')
