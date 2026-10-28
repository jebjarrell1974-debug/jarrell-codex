"""The first screen, which is the only one a lot of people will judge.

What matters is not that it exists but that a first-time visitor actually
lands on it, that it reads at the default size on a phone with no sideways
scrolling, that every button it promises is really there, and that it gets
out of the way afterwards and stays out.
"""
import asyncio, sys
from playwright.async_api import async_playwright

BASE = 'http://127.0.0.1:8777/'
fails, errs = [], []


def chk(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name +
          (f'  {detail}' if detail and not cond else ''))
    if not cond:
        fails.append(name + ' :: ' + str(detail)[:300])


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--no-proxy-server'])
        ctx = await b.new_context(viewport={'width': 390, 'height': 844},
                                  device_scale_factor=2, is_mobile=True,
                                  has_touch=True)
        pg = await ctx.new_page()
        pg.on('console', lambda m: errs.append(f'[{m.type}] {m.text}')
              if m.type == 'error' else None)
        pg.on('pageerror', lambda e: errs.append(f'[pageerror] {e}'))
        pg.on('requestfailed', lambda r: errs.append(f'[fail] {r.url[-40:]}'))

        await pg.goto(BASE, wait_until='load')
        await pg.evaluate("""async () => {
            const rs = await navigator.serviceWorker.getRegistrations();
            await Promise.all(rs.map(r => r.unregister()));
            const ks = await caches.keys();
            await Promise.all(ks.map(k => caches.delete(k)));
            localStorage.clear();
        }""")

        # ---- a first visit, which is the whole point -------------------
        print('somebody opens the link for the first time')
        await pg.goto(BASE, wait_until='load')
        await pg.wait_for_function(
            "() => document.querySelector('#view h1')", timeout=15000)
        await pg.wait_for_timeout(300)
        chk('they land on the welcome, not in the middle of John',
            'welcome' in pg.url, pg.url)
        h1 = await pg.inner_text('#view h1')
        chk('it says what it is called', 'Jarrell Codex' in h1, h1)
        txt = await pg.inner_text('#view')
        for want, label in [
            ('Hebrew and Greek', 'it says what the book actually contains'),
            ('free', 'it says it is free'),
            ('no account', 'it says there is no account'),
            ('nothing here watches', 'it says it does not watch you'),
        ]:
            chk(label, want in txt, txt[:300])

        print('\nthe five things it promises')
        for want, label in [
            ('Listen', 'the Listen button'),
            ('Aa', 'the Aa button'),
            ('bigger', 'making the words bigger'),
            ('Tap any Hebrew or Greek word', 'tapping a word'),
            ('markers under a verse', 'the verse markers'),
            ('list of books', 'the book list'),
            ('searches the whole Bible', 'search'),
        ]:
            chk(f'it mentions {label}', want in txt, '')
        ndemo = await pg.locator('.demo').count()
        chk('each tip draws the button it is talking about', ndemo >= 5, ndemo)
        boxes = [await e.bounding_box() for e in await pg.locator('.demo').all()]
        small = [b for b in boxes if b and (b['width'] < 44 or b['height'] < 44)]
        chk('the drawn buttons are the real 44px size', not small, small[:2])

        print('\nit reads properly on a phone')
        fs = await pg.evaluate(
            "() => getComputedStyle(document.documentElement).fontSize")
        chk('at the default text size', fs == '19px', fs)
        sw = await pg.evaluate(
            "() => document.documentElement.scrollWidth - window.innerWidth")
        chk('with no sideways scrolling', sw <= 1, sw)
        start = pg.locator('.start')
        chk('there is one Start reading button', await start.count() == 1)
        sb = await start.bounding_box()
        chk('and it is a big target', sb['height'] >= 56, sb['height'])
        chk('it spans the screen', sb['width'] > 300, sb['width'])
        # the honest caveat about the one thing that needs a signal
        chk('it says the readings need a connection',
            'needs an internet connection' in txt, '')
        chk('and that everything else does not',
            'everything else does not' in txt, '')

        print('\nputting it on the home screen')
        chk('the first screen offers it',
            'home screen' in txt.lower(), txt[:200])
        chk('and says why it is worth doing',
            'opens straight to where you left off' in txt, '')
        chk('and that nothing comes from a shop',
            'Nothing is installed from a shop' in txt, '')
        # Chrome in this harness does not fire beforeinstallprompt, which is
        # the same position Safari is always in: no prompt to offer, so the
        # words have to carry it. The button stays hidden until a prompt
        # actually exists, because a button that does nothing is worse than
        # none.
        hidden = await pg.evaluate(
            "() => { const b = document.getElementById('installBtn');"
            " return b ? b.hidden : 'no button'; }")
        chk('the button is hidden until the browser offers a prompt',
            hidden is True or hidden == 'no button', hidden)
        how = await pg.evaluate("() => installHow()")
        chk('and the written route is one route, not a list',
            how.count('Add to Home') + how.count('Add to home') == 1, how)
        # the right route for the phone in hand
        ios = await pg.evaluate("""() => {
            const real = navigator.userAgent;
            Object.defineProperty(navigator, 'userAgent',
                { get: () => 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)',
                  configurable: true });
            const s = installHow();
            Object.defineProperty(navigator, 'userAgent',
                { get: () => real, configurable: true });
            return s;
        }""")
        chk('an iPhone is told about the share button',
            'share button' in ios and 'Safari' in ios, ios)
        chk('and not about three dots', 'three dots' not in ios, ios)

        print('\nstarting to read')
        await start.click()
        await pg.wait_for_function(
            "() => document.querySelectorAll('#view .v').length > 0", timeout=15000)
        chk('it opens a chapter', await pg.locator('#view .v').count() > 10)
        chk('John 3, as it said it would',
            'John 3' in await pg.inner_text('#view h1'),
            await pg.inner_text('#view h1'))

        print('\nand then stays out of the way')
        await pg.goto(BASE, wait_until='load')
        await pg.wait_for_function(
            "() => document.querySelectorAll('#view .v').length > 0", timeout=15000)
        chk('a second visit goes straight to the text',
            'welcome' not in pg.url, pg.url)
        await pg.reload(wait_until='load')
        await pg.wait_for_timeout(1500)
        chk('and a reload after that too', 'welcome' not in pg.url, pg.url)

        print('\nbut can be asked for again')
        await pg.goto(BASE + '#/about', wait_until='load')
        await pg.wait_for_function(
            "() => document.querySelector('#view h1')", timeout=15000)
        link = pg.locator('[data-go="welcome"]')
        chk('About offers it', await link.count() == 1)
        await link.click()
        await pg.wait_for_function(
            "() => document.querySelector('.start')", timeout=15000)
        chk('and it comes back', await pg.locator('.start').count() == 1)

        print('\nit survives a colour scheme and a bigger size')
        await pg.goto(BASE + '#/welcome', wait_until='load')
        await pg.wait_for_function("() => document.querySelector('.start')",
                                   timeout=15000)
        await pg.evaluate("() => { S.scheme = 'night'; S.fs = 30; applyDisplay(); }")
        await pg.wait_for_timeout(300)
        sw = await pg.evaluate(
            "() => document.documentElement.scrollWidth - window.innerWidth")
        chk('no sideways scrolling at 30px in the dark', sw <= 1, sw)
        bg = await pg.evaluate(
            "() => getComputedStyle(document.body).backgroundColor")
        chk('the dark palette applies here too',
            bg not in ('rgb(252, 251, 248)', 'rgba(0, 0, 0, 0)'), bg)
        sb = await pg.locator('.start').bounding_box()
        chk('the Start button still fits', sb['width'] <= 390, sb['width'])

        await b.close()

asyncio.run(main())
print('\nconsole errors:', len(errs))
for e in errs[:8]:
    print('   ', e)
print('\n' + ('FAILED' if fails or errs else 'ALL CHECKS PASSED'))
for f in fails:
    print('   -', f)
sys.exit(1 if fails or errs else 0)
