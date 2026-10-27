# -*- coding: utf-8 -*-
"""The first screen, as the live site serves it."""
import sys, time, urllib.request

B = 'https://jebjarrell1974-debug.github.io/jarrell-codex/'
fails = []


def chk(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name +
          (('  ' + str(detail)[:150]) if detail and not cond else ''))
    if not cond:
        fails.append(name)


def grab(path):
    r = urllib.request.Request(B + path, headers={
        'User-Agent': 'jarrell-codex-verify', 'Cache-Control': 'no-cache'})
    with urllib.request.urlopen(r, timeout=60) as h:
        return h.read().decode('utf-8')


js = None
for attempt in range(20):
    js = grab('app.js')
    if 'welcomeView' in js:
        break
    print(f'  waiting for the deploy... ({attempt + 1})')
    time.sleep(30)

print('the code')
chk('the welcome page is published', 'function welcomeView' in js)
chk('a first visit is sent to it', "go('#/welcome', true)" in js)
chk('and the route exists', "h === 'welcome'" in js)
chk('the Start reading button is wired to the click handler',
    '[data-startreading]' in js and 'startreading' in js)
chk('it is shown once and remembered', 'codex-seen' in js)
chk('About can bring it back', 'data-go="welcome"' in js)
for frag, label in [
    ('It can read itself to you', 'it tells them about Listen'),
    ('You can make the words bigger', 'and about text size'),
    ('Tap any Hebrew or Greek word', 'and about the words'),
    ('markers under a verse', 'and about the verse markers'),
    ('needs an\n     internet connection', 'and says what needs a signal'),
    ('nothing here watches what you read', 'and that nothing watches them'),
]:
    chk(label, frag in js)

css = grab('app.css')
chk('the first screen is styled', '.start{' in css and '.tip{' in css)
chk('the drawn buttons keep a 44px target', 'min-width:44px' in css)
chk('and the Start button is 60px tall', 'min-height:60px' in css)

sw = grab('sw.js')
chk('the build is stamped, so returning readers get this',
    "const BUILD = '" in sw)

print('\n' + ('FAILED: ' + ', '.join(fails) if fails
              else 'THE FIRST SCREEN IS GOOD'))
sys.exit(1 if fails else 0)
