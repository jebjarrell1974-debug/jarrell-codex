"""The audio player, and the colour/chronology split it shipped with.

archive.org is unreachable from this container, so every request to it is
answered with a 600-second silent file. That is not a cheat: what is being
tested is the player's own behaviour - does it resolve the right file, say
honestly what that file covers, and land the estimate where the verse
counts say it should - none of which depends on the bytes being a reading.
Whether the URLs themselves are live is checked separately, from a machine
with open internet.
"""
import asyncio, io, json, os, sys
from playwright.async_api import async_playwright

BASE = 'http://127.0.0.1:8777/'
SITE = '/home/claude/site'
SIL = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'silence600.mp3')
DUR = 600.058776
fails, errs = [], []

A = json.load(io.open(os.path.join(SITE, 'data/audio.json'), encoding='utf-8'))
BOOKS = json.load(io.open(os.path.join(SITE, 'data/books.json'), encoding='utf-8'))


def chk(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name + (f'  {detail}' if detail and not cond else ''))
    if not cond:
        fails.append(name + ' :: ' + str(detail)[:300])


def fraction(f, i):
    total = sum(f['vs'])
    return sum(f['vs'][:i]) / total if total and i > 0 else 0.0


# ---------------------------------------------------------------- the index
print('the index itself')
nch = {b[0]: b[3] for b in BOOKS['books']}
want = {f'{c}.{n}' for c in nch for n in range(1, nch[c] + 1)}
chk('every chapter in the canon has a reading', set(A['chapters']) == want,
    sorted(want - set(A['chapters']))[:6])
bad = [k for k, (fi, i) in A['chapters'].items()
       if A['files'][fi]['ch'][i] != k]
chk('every chapter points at a file that lists it', not bad, bad[:6])
bad = [f['item'] for f in A['files'] if f['item'] not in A['sources']]
chk('every file names a credited source', not bad, bad[:4])
bad = [f['u'] for f in A['files'] if len(f['ch']) != len(f['vs'])]
chk('every file carries one verse count per chapter', not bad, bad[:4])
bad = [f['u'] for f in A['files'] if not f['u'].startswith('https://archive.org/')]
chk('every url is on archive.org over https', not bad, bad[:4])
lic = {s.get('licence', '') for s in A['sources'].values()}
chk('every source is public domain',
    all('publicdomain' in l for l in lic), sorted(lic))
# verse counts must match the chapters the reader actually gets
mis = []
for f in A['files'][:40]:
    for k, v in zip(f['ch'], f['vs']):
        d = json.load(io.open(os.path.join(SITE, 'data/ch', k + '.json'), encoding='utf-8'))
        if len(d['v']) != v:
            mis.append((k, v, len(d['v'])))
chk('verse counts match the chapter files', not mis, mis[:4])


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--no-proxy-server', '--autoplay-policy=no-user-gesture-required'])
        ctx = await b.new_context(viewport={'width': 390, 'height': 844},
                                  device_scale_factor=2, is_mobile=True, has_touch=True)
        pg = await ctx.new_page()
        pg.on('console', lambda m: errs.append(f'[{m.type}] {m.text}') if m.type == 'error' else None)
        pg.on('pageerror', lambda e: errs.append(f'[pageerror] {e}'))

        asked = []

        async def fake(route):
            asked.append(route.request.url)
            await route.fulfill(status=200, path=SIL,
                               headers={'content-type': 'audio/mpeg',
                                        'accept-ranges': 'bytes'})
        await pg.route('**archive.org/**', fake)

        await pg.goto(BASE, wait_until='load')
        await pg.evaluate("""async () => {
            const rs = await navigator.serviceWorker.getRegistrations();
            await Promise.all(rs.map(r => r.unregister()));
            const ks = await caches.keys();
            await Promise.all(ks.map(k => caches.delete(k)));
        }""")

        async def reset(h):
            await pg.evaluate("history.replaceState(null,'','#/_')")
            await pg.goto(BASE + h, wait_until='load')
            await pg.wait_for_function(
                "() => document.querySelector('#view') && "
                "!document.querySelector('#view .load')", timeout=15000)
            await pg.wait_for_timeout(200)

        async def listen(h):
            await reset(h)
            await pg.locator('.listen').first.click()
            await pg.wait_for_function(
                "() => { const p=document.getElementById('player');"
                " return p && !p.hidden && !/Finding a reading/.test("
                "document.getElementById('plTxt').textContent); }", timeout=15000)
            await pg.wait_for_timeout(500)

        # ------------------------------------------------- the control itself
        print('\nthe Listen control')
        await reset('#/Jhn.3')
        # one at the head of the chapter and one at its foot: Psalm 119 runs
        # to 176 verses, and someone who reaches the end of it should not have
        # to scroll back to the top to find the button
        nl = await pg.locator('.listen').count()
        chk('a chapter offers a Listen control at each end', nl == 2, nl)
        chk('it says so in words, not only an icon',
            'listen' in (await pg.locator('.listen').first.inner_text()).lower(),
            await pg.locator('.listen').first.inner_text())
        chk('the one at the foot names the chapter',
            'John 3' in await pg.locator('.listen').last.inner_text(),
            await pg.locator('.listen').last.inner_text())
        box = await pg.locator('.listen').first.bounding_box()
        chk('the control clears a 48px tap target', box['height'] >= 48, box['height'])
        chk('the player starts hidden', await pg.get_attribute('#player', 'hidden') is not None)

        # ------------------------------------------- a chapter inside a file
        print('\nJohn 3, which sits inside a longer reading')
        await listen('#/Jhn.3')
        fi, i = A['chapters']['Jhn.3']
        f = A['files'][fi]
        chk('the file is the one the index names',
            await pg.get_attribute('#plAudio', 'src') == f['u'],
            await pg.get_attribute('#plAudio', 'src'))
        chk('archive.org was actually asked for it', any('archive.org' in u for u in asked))
        txt = await pg.inner_text('#plTxt')
        chk('the bar names the chapter being read', 'John 3' in txt, txt)
        chk('it says the recording covers more than this chapter',
            'covers' in txt and str(len(f['ch'])) in txt, txt)
        note = await pg.inner_text('#plNote')
        chk('it calls the starting point an estimate', 'estimate' in note.lower(), note)
        chk('it says the estimate comes from verse counts, not a timing',
            'verse count' in note.lower()
            and ('not a real timing' in note.lower()
                 or 'rather than a real timing' in note.lower()), note)
        chk('it offers to start at the beginning instead',
            await pg.locator('[data-aufrom]').count() == 1)
        chk('it credits LibriVox and the public domain',
            'LibriVox' in note and 'ublic domain' in note, note)
        chk('it says the audio is streamed, not stored here',
            'not stored here' in note, note)
        # the estimate must land where the verse counts say
        want_t = DUR * fraction(f, i)
        got = await pg.evaluate("() => document.getElementById('plAudio').currentTime")
        chk(f'it seeks to the estimated position ({want_t:.0f}s)',
            abs(got - want_t) < 6, f'wanted {want_t:.1f}, got {got:.1f}')
        chk('the note reports the position it actually used',
            'about ' in await pg.inner_text('#plNote'), await pg.inner_text('#plNote'))

        print('\nstarting at the beginning instead')
        await pg.click('[data-aufrom]')
        await pg.wait_for_timeout(300)
        got = await pg.evaluate("() => document.getElementById('plAudio').currentTime")
        chk('it goes back to 0:00', got < 2, got)
        chk('and says so', 'beginning of the recording' in await pg.inner_text('#plNote'),
            await pg.inner_text('#plNote'))

        # ---------------------------------------------- a chapter on its own
        print('\nJoshua 6, read as a file of its own')
        await listen('#/Jos.6')
        fi2, i2 = A['chapters']['Jos.6']
        f2 = A['files'][fi2]
        chk('the index has it alone in its file', f2['one'] and len(f2['ch']) == 1,
            len(f2['ch']))
        txt = await pg.inner_text('#plTxt')
        chk('the bar says it is a recording of this chapter alone',
            'on its own' in txt, txt)
        chk('it claims no range it cannot back up', 'covers' not in txt, txt)
        note = await pg.inner_text('#plNote')
        chk('no estimate is offered where none is needed',
            'estimate' not in note.lower(), note)
        chk('and no jump-to-the-start button either',
            await pg.locator('[data-aufrom]').count() == 0)
        got = await pg.evaluate("() => document.getElementById('plAudio').currentTime")
        chk('it starts at the beginning', got < 2, got)

        # --------------------------------------------- the first chapter of a set
        print('\nGenesis 1, first chapter of a longer reading')
        await listen('#/Gen.1')
        note = await pg.inner_text('#plNote')
        chk('no estimate, because it starts where the file starts',
            'estimate' not in note.lower(), note)
        got = await pg.evaluate("() => document.getElementById('plAudio').currentTime")
        chk('it starts at 0:00', got < 2, got)

        # ------------------------------------------- the text stays readable
        print('\nthe bar does not sit on top of the text')
        await listen('#/Psa.23')
        chk('body is padded while the bar is open',
            await pg.evaluate("() => parseFloat(getComputedStyle(document.body).paddingBottom) > 200"),
            await pg.evaluate("() => getComputedStyle(document.body).paddingBottom"))
        last = pg.locator('.v').last
        lb = await last.bounding_box()
        pb = await pg.locator('#player').bounding_box()
        await pg.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
        await pg.wait_for_timeout(200)
        lb = await pg.locator('.v').last.bounding_box()
        pb = await pg.locator('#player').bounding_box()
        chk('the last verse is above the bar, not behind it',
            lb['y'] + lb['height'] <= pb['y'] + 2,
            f"verse ends {lb['y']+lb['height']:.0f}, bar starts {pb['y']:.0f}")

        print('\nkeeping the reading while paging through chapters')
        src_before = await pg.get_attribute('#plAudio', 'src')
        t_before = await pg.evaluate("() => document.getElementById('plAudio').currentTime")
        await pg.evaluate("() => location.hash = '#/Psa.24'")
        await pg.wait_for_timeout(600)
        chk('the player survives moving to the next chapter',
            await pg.get_attribute('#player', 'hidden') is None)
        chk('and keeps playing the same file',
            await pg.get_attribute('#plAudio', 'src') == src_before)
        t_after = await pg.evaluate("() => document.getElementById('plAudio').currentTime")
        chk('without starting over', t_after >= t_before - 1,
            f'{t_before:.1f} -> {t_after:.1f}')

        print('\nstopping')
        await pg.click('#plX')
        await pg.wait_for_timeout(250)
        chk('the bar closes', await pg.get_attribute('#player', 'hidden') is not None)
        chk('the audio is released',
            not await pg.evaluate("() => document.getElementById('plAudio').getAttribute('src')"))
        chk('and the padding goes with it',
            await pg.evaluate("() => parseFloat(getComputedStyle(document.body).paddingBottom) < 60"))

        # ------------------------------------------------ offline is honest
        print('\noffline, where a streamed reading cannot work')
        await reset('#/Jhn.3')
        await pg.evaluate("() => Object.defineProperty(navigator,'onLine',{get:()=>false})")
        await pg.locator('.listen').first.click()
        await pg.wait_for_timeout(1200)
        note = await pg.inner_text('#plNote')
        chk('it says you are offline', 'offline' in note.lower(), note)
        chk('it says the readings are streamed', 'streamed' in note.lower(), note)
        chk('and that the text itself still works',
            'still works offline' in note.lower(), note)

        print('\ncrediting the readings')
        await reset('#/about')
        ab = await pg.inner_text('#view')
        chk('LibriVox is in the list of sources', 'LibriVox' in ab)
        chk('so is archive.org, where the files actually live', 'archive.org' in ab)
        chk('and it says nothing is stored here', 'Nothing is stored here' in ab, ab[:0])
        chk('the photographs are credited too', 'Wikimedia Commons' in ab)
        chk('and the engravings', 'Dor' in ab and '1866' in ab)
        ft = await pg.inner_text('.foot') if await pg.locator('.foot').count() else ''
        await reset('#/Jhn.3')
        ft = await pg.inner_text('.foot')
        chk('the footer names the readings too',
            'LibriVox' in ft and 'archive.org' in ft, ft[-200:])

        print('\nthe Reading sheet points at the recordings')
        await pg.click('#btnAa')
        await pg.wait_for_timeout(250)
        sh = await pg.inner_text('#sheet')
        chk('it offers to have the text read aloud',
            'read to you' in sh.lower(), sh[:200])
        chk('and says the recordings need a connection',
            'need a connection' in sh.lower(), sh[:300])
        await pg.evaluate("() => closeSheet()")
        await pg.wait_for_timeout(200)

        # ----------------------------------- the colour / chronology split
        print('\ncolour and chronology, which used to share one setting')
        await reset('#/Jhn.3')
        await pg.click('#btnAa')
        await pg.wait_for_timeout(200)
        await pg.click('[data-setscheme3="night"]')
        await pg.wait_for_timeout(250)
        chk('picking night applies it',
            await pg.get_attribute('html', 'data-scheme') == 'night',
            await pg.get_attribute('html', 'data-scheme'))
        await reset('#/Jhn.3')
        chk('and it survives a reload',
            await pg.get_attribute('html', 'data-scheme') == 'night',
            await pg.get_attribute('html', 'data-scheme'))
        await reset('#/chrono')
        rows = await pg.locator('.hit').count()
        chk('the timeline still has its events after a colour was chosen',
            rows > 50, rows)
        sel = await pg.locator('.opt.on').count()
        chk('a chronology is still selected', sel >= 1, sel)
        # and choosing a chronology must not change the colour
        opts = pg.locator('[data-setscheme2]')
        if await opts.count() > 1:
            await opts.nth(1).click()
            await pg.wait_for_timeout(400)
        chk('choosing a chronology leaves the colour alone',
            await pg.get_attribute('html', 'data-scheme') == 'night',
            await pg.get_attribute('html', 'data-scheme'))
        await reset('#/chrono')
        chk('both survive together',
            await pg.get_attribute('html', 'data-scheme') == 'night'
            and await pg.locator('.hit').count() > 0)

        await b.close()

asyncio.run(main())
real = [e for e in errs if 'archive.org' not in e and 'MEDIA' not in e.upper()]
print('\nconsole errors:', len(real))
for e in real[:10]:
    print('   ', e)
print(f'\n{"FAILED: " + str(len(fails)) if fails else "all audio checks passed"}')
for f in fails:
    print('   -', f)
sys.exit(1 if fails or real else 0)
