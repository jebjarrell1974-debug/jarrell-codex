# -*- coding: utf-8 -*-
"""The player, as the live site serves it, and every reading it points at."""
import json, sys, time, urllib.request

B = 'https://jebjarrell1974-debug.github.io/jarrell-codex/'
fails = []

def chk(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name +
          (('  ' + str(detail)[:150]) if detail and not cond else ''))
    if not cond:
        fails.append(name)

def grab(path, binary=False):
    r = urllib.request.Request(B + path,
                               headers={'User-Agent': 'jarrell-codex-verify',
                                        'Cache-Control': 'no-cache'})
    with urllib.request.urlopen(r, timeout=60) as h:
        d = h.read()
    return d if binary else d.decode('utf-8')

# Pages can take a minute to publish. Wait for the new shape rather than
# reporting a stale deploy as a failure.
ix = None
for attempt in range(20):
    try:
        ix = json.loads(grab('data/audio.json'))
    except Exception as e:
        print('  index not readable yet:', repr(e)[:70])
        ix = None
    if ix and 'files' in ix:
        break
    print(f'  waiting for the deploy... ({attempt + 1})')
    time.sleep(30)
    ix = None
if not ix or 'files' not in ix:
    print('\nFAILED: the live index is still the old shape after 10 minutes')
    sys.exit(1)

print('the index')
chk('1189 chapters', len(ix['chapters']) == 1189, len(ix['chapters']))
chk('375 files', len(ix['files']) == 375, len(ix['files']))
bad = [k for k, (fi, i) in ix['chapters'].items() if ix['files'][fi]['ch'][i] != k]
chk('every chapter points at a file that lists it', not bad, bad[:4])
chk('every source is public domain',
    all('publicdomain' in s.get('licence', '') for s in ix['sources'].values()))

print('\nthe code')
js = grab('app.js')
for frag, label in [('data-listen', 'the Listen hook'),
                    ("audio.json", 'the audio index is fetched'),
                    ('auFraction', 'the verse-count estimate'),
                    ('not stored here', 'it says the audio is not hosted here'),
                    ('S.chrono', 'chronology has its own setting')]:
    chk(label, frag in js)
chk('the colour no longer doubles as a chronology id',
    'scheme_id === S.scheme' not in js)
html = grab('index.html')
chk('the player markup is served', 'id="plAudio"' in html and 'id="player"' in html)
css = grab('app.css')
chk('the player is styled', '.player{' in css and 'body.playing' in css)

print('\nevery reading is actually there')
# Serial, with retries. Concurrency here produced twenty phantom
# failures: archive.org rate-limits with a 500, which is indistinguishable
# from a dead file unless you try again. A missing file returns 404 and
# keeps returning it.
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

bad, small, unsure, retried, total = [], [], [], 0, 0
urls = [f['u'] for f in ix['files']]
for i, u in enumerate(urls, 1):
    st, ct, ln, tries = head(u)
    total += ln
    if tries > 1 and st == 200:
        retried += 1
    if st == 404:
        bad.append((st, 'not found', u))
    elif st != 200:
        # The server would not say. Ask again after it has had a rest.
        unsure.append(u)
    elif 'audio' not in ct and 'mpeg' not in ct:
        bad.append((st, 'not audio: ' + ct, u))
    elif ln < 200000:
        small.append((ln, u))
    if i % 75 == 0:
        print(f'  ...{i}/{len(urls)}  ({len(bad)} gone, {len(unsure)} unclear, '
              f'{retried} needed a retry)')
    time.sleep(0.15)

if unsure:
    print(f'\n  {len(unsure)} came back 5xx. That is archive.org declining to '
          f'answer, not a missing file,\n  so: a minute off, then ask again.')
    time.sleep(60)
    for u in unsure:
        st, ct, ln, _ = head(u, tries=5)
        total += ln
        if st == 200 and ('audio' in ct or 'mpeg' in ct):
            print(f'    ok on a second pass: {u.rsplit("/", 1)[-1]}')
        else:
            bad.append((st, ct, u))
        time.sleep(1)
chk(f'all {len(urls)} readings reachable', not bad, bad[:8])
if unsure and not bad:
    print(f'       {len(unsure)} needed a second pass after a rest')
chk('none suspiciously small', not small, small[:4])
print(f'       {total / 1024 / 1024 / 1024:.2f} GB of audio, streamed, 0 bytes hosted here')
print(f'       {retried} needed a retry, which is rate limiting, not a missing file')

print('\n' + ('FAILED: ' + ', '.join(fails) if fails else 'THE PLAYER IS GOOD'))
sys.exit(1 if fails else 0)
