"""Moving between the lookup tools, and seeing verses rather than numbers.

Both of these come from one message: a list of bare chapter-and-verse
numbers is a table of contents for a concordance rather than a
concordance, and a panel with no way back makes every lookup a one-way
trip. So what is tested here is whether a reader can actually get round.
"""
import asyncio, io, json, sys
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
        pg.on('requestfailed', lambda r: errs.append(f'[fail] {r.url[-50:]}'))

        await pg.goto(BASE, wait_until='load')
        await pg.evaluate("""async () => {
            const rs = await navigator.serviceWorker.getRegistrations();
            await Promise.all(rs.map(r => r.unregister()));
            const ks = await caches.keys();
            await Promise.all(ks.map(k => caches.delete(k)));
            localStorage.setItem('codex-seen','1');
        }""")

        async def chapter(ref):
            # A goto to the same hash fires no hashchange, so route() never
            # runs and the panel stays open over the text. Close it first.
            await pg.evaluate("() => { try { closeSheet(); } catch {} }")
            await pg.goto(BASE + '#/' + ref, wait_until='load')
            await pg.wait_for_function(
                "() => document.querySelectorAll('#view .v').length > 0",
                timeout=20000)

        # ---------------------------------------------- the concordance
        print('the concordance, which is the thing he asked for')
        await chapter('Jhn.3')
        await pg.locator('.w.grk').first.click()
        await pg.wait_for_function(
            "() => /Concordance/.test(document.getElementById('sheet').textContent)",
            timeout=20000)
        conc = pg.locator('[data-conc]').first
        label = await conc.inner_text()
        chk('the word study offers it, with a count', 'Concordance' in label, label)
        await conc.click()
        await pg.wait_for_function(
            "() => document.querySelectorAll('#sheet .hit').length > 0", timeout=20000)
        n = await pg.locator('#sheet .hit').count()
        chk('it lists the occurrences', n > 1, n)
        # the thing that was missing
        await pg.wait_for_function(
            "() => [...document.querySelectorAll('#sheet .vt')]"
            ".filter(e => e.textContent.trim()).length > 0", timeout=20000)
        filled = await pg.evaluate(
            "() => [...document.querySelectorAll('#sheet .vt')]"
            ".filter(e => e.textContent.trim()).length")
        chk('every one carries its verse, not just its number',
            filled >= n - 2, f'{filled} of {n}')
        first = await pg.locator('#sheet .hit').first.inner_text()
        chk('so a line reads as a reference and then the words',
            len(first.split('\n')[-1].strip()) > 25, first[:120])
        marks = await pg.locator('#sheet .vt mark').count()
        chk('and the word itself is picked out', marks > 0, marks)

        # ---------------------------------------------- getting back
        print('\ngetting back out again')
        back = pg.locator('#sheet [data-sheetback]')
        chk('the concordance offers the way back', await back.count() == 1)
        btxt = await back.inner_text()
        chk('and says where to, by name', 'the word' in btxt, btxt)
        await pg.locator('#sheet [data-dict]').first.click()
        # Not "the panel mentions the dictionary": the concordance now has
        # a button that says so, which was true the instant it was drawn
        # and let this read the label a step too early. Wait for the verse
        # list to be gone, which only the dictionary step is.
        await pg.wait_for_function(
            "() => !document.querySelector('#sheet .hit[data-ref]')"
            " && /dictionary/i.test(document.getElementById('sheet').textContent)",
            timeout=20000)
        btxt = await pg.locator('#sheet [data-sheetback]').inner_text()
        chk('three deep, it points back to the concordance',
            'concordance' in btxt.lower(), btxt)
        await pg.locator('#sheet [data-sheetback]').click()
        await pg.wait_for_function(
            "() => document.querySelectorAll('#sheet .hit').length > 0", timeout=20000)
        chk('and going back lands on the concordance again',
            await pg.locator('#sheet .hit').count() > 1)
        await pg.locator('#sheet [data-sheetback]').click()
        await pg.wait_for_function(
            "() => /Concordance/.test(document.getElementById('sheet').textContent)"
            " && !document.querySelector('#sheet .hit')", timeout=20000)
        chk('and again on the word it started from',
            await pg.locator('#sheet [data-conc]').count() >= 1)
        chk('which is the bottom, so there is no way back from it',
            await pg.locator('#sheet [data-sheetback]').count() == 0)

        # ---------------------------------------------- the other lists
        print('\nthe other lists that were bare numbers')
        await chapter('Jhn.3')
        await pg.locator('[data-k="xref"]').first.click()
        await pg.wait_for_function(
            "() => [...document.querySelectorAll('#sheet .vt')]"
            ".filter(e => e.textContent.trim()).length > 0", timeout=20000)
        nx = await pg.locator('#sheet .hit').count()
        fx = await pg.evaluate(
            "() => [...document.querySelectorAll('#sheet .vt')]"
            ".filter(e => e.textContent.trim()).length")
        chk('cross-references carry their verses', fx >= nx - 2, f'{fx} of {nx}')

        await chapter('Luk.2')
        await pg.locator('[data-k="place"]').first.click()
        await pg.wait_for_timeout(2500)
        np = await pg.locator('#sheet .hit').count()
        if np:
            fp = await pg.evaluate(
                "() => [...document.querySelectorAll('#sheet .vt')]"
                ".filter(e => e.textContent.trim()).length")
            chk('a place lists its verses with their words', fp >= np - 2,
                f'{fp} of {np}')

        # ---------------------------------------------- it follows the reader
        print('\nit answers in the translation being read')
        await chapter('Jhn.3')
        await pg.evaluate("() => { S.tx = 'YLT'; save(); }")
        await pg.locator('[data-k="xref"]').first.click()
        await pg.wait_for_function(
            "() => [...document.querySelectorAll('#sheet .vt')]"
            ".filter(e => e.textContent.trim()).length > 0", timeout=20000)
        ylt = await pg.locator('#sheet .vt').first.inner_text()
        await pg.evaluate("() => { S.tx = 'KJV'; save(); }")
        await chapter('Jhn.3')
        await pg.locator('[data-k="xref"]').first.click()
        await pg.wait_for_function(
            "() => [...document.querySelectorAll('#sheet .vt')]"
            ".filter(e => e.textContent.trim()).length > 0", timeout=20000)
        kjv = await pg.locator('#sheet .vt').first.inner_text()
        chk('switching translation changes the quoted text', ylt != kjv,
            f'{ylt[:50]!r} vs {kjv[:50]!r}')

        # ---------------------------------------------- the guide
        print('\nthe written guide')
        await pg.goto(BASE + '#/guide', wait_until='load')
        await pg.wait_for_function("() => document.querySelector('#view h1')",
                                   timeout=20000)
        g = await pg.inner_text('#view')
        for want, label in [
            ('Concordance: 321 verses', 'it shows what the concordance line looks like'),
            ('Back to the word', 'it explains the way back'),
            ('Aa', 'it covers text size'),
            ('Listen', 'it covers the readings'),
            ('three lines', 'it covers getting around'),
            ('Easton', 'it says what the dictionary is'),
            ('no signal', 'it covers working offline'),
            ('disputed', 'it says where the app disagrees with itself'),
        ]:
            chk(label, want in g, g[:200])
        sw = await pg.evaluate(
            "() => document.documentElement.scrollWidth - window.innerWidth")
        chk('it fits the screen', sw <= 1, sw)
        chk('About links to it',
            await pg.evaluate(
                "async () => { location.hash = '#/about';"
                " await new Promise(r => setTimeout(r, 1200));"
                " return !!document.querySelector('[data-go=\\\"guide\\\"]'); }"))

        await b.close()

asyncio.run(main())
real = [e for e in errs if 'favicon' not in e]
print('\nconsole errors:', len(real))
for e in real[:8]:
    print('   ', e)
print('\n' + ('FAILED' if fails or real else 'ALL CHECKS PASSED'))
for f in fails:
    print('   -', f)
sys.exit(1 if fails or real else 0)
