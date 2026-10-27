"""Open a wide spread of chapters and look for anything broken.

The targeted tests check features. This checks the whole corpus: every
book, the awkward chapters, and whatever the data does that I did not
think to assert.
"""
import asyncio, json, random, sys
from playwright.async_api import async_playwright
BASE = 'http://127.0.0.1:8777/'

async def main():
    problems, errors = [], []
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--no-proxy-server'])
        ctx = await b.new_context(viewport={'width': 390, 'height': 844},
                                  is_mobile=True, has_touch=True)
        pg = await ctx.new_page()
        pg.on('pageerror', lambda e: errors.append(f'pageerror: {e}'))
        pg.on('console', lambda m: errors.append(f'console.error: {m.text[:160]}')
              if m.type == 'error' else None)
        await pg.goto(BASE, wait_until='load')
        await pg.evaluate("""async () => {
            const rs = await navigator.serviceWorker.getRegistrations();
            await Promise.all(rs.map(r => r.unregister()));
            const ks = await caches.keys();
            await Promise.all(ks.map(k => caches.delete(k))); }""")
        await pg.reload(wait_until='load'); await pg.wait_for_timeout(2500)

        books = await pg.evaluate("fetch('data/books.json').then(r=>r.json())")
        rng = random.Random(7)
        targets = []
        for code, _order, _t, nch in books['books']:
            targets.append((code, 1))                       # first of every book
            if nch > 1: targets.append((code, nch))         # last of every book
            if nch > 3: targets.append((code, rng.randint(2, nch - 1)))
        # the ones most likely to be strange
        targets += [('Psa', 119), ('Psa', 117), ('Psa', 3), ('Num', 26),
                    ('Oba', 1), ('Mrk', 16), ('Jhn', 8), ('Est', 1), ('Dan', 2)]
        seen = set(); ordered = []
        for t in targets:
            if t not in seen: seen.add(t); ordered.append(t)
        print(f'crawling {len(ordered)} chapters across all {len(books["books"])} books\n')

        for i, (code, ch) in enumerate(ordered):
            before = len(errors)
            try:
                await pg.goto(f'{BASE}#/{code}.{ch}', wait_until='load')
                await pg.wait_for_function(
                    "() => { const v=document.querySelector('#view');"
                    "  return v && !v.querySelector('.load'); }", timeout=20000)
            except Exception as e:
                problems.append(f'{code}.{ch}: did not render ({str(e)[:90]})'); continue
            info = await pg.evaluate("""() => {
                const v = document.querySelector('#view');
                const h = v.querySelector('h1');
                return {
                  heading: h ? h.textContent.trim() : '',
                  verses: v.querySelectorAll('.v').length,
                  words: v.querySelectorAll('.w').length,
                  eng: [...v.querySelectorAll('.eng')].filter(e=>e.textContent.trim().length>3).length,
                  overflow: document.documentElement.scrollWidth - window.innerWidth,
                  undef: /undefined|\\bNaN\\b|\\[object Object\\]/.test(v.textContent),
                }; }""")
            if info['undef']:
                problems.append(f'{code}.{ch}: renders undefined/NaN/[object Object]')
            if info['verses'] == 0:
                problems.append(f'{code}.{ch}: no verses rendered')
            if info['words'] == 0:
                problems.append(f'{code}.{ch}: no original-language words')
            if info['eng'] == 0:
                problems.append(f'{code}.{ch}: no English text')
            if info['overflow'] > 1:
                problems.append(f'{code}.{ch}: horizontal overflow {info["overflow"]}px')
            if not info['heading'] or info['heading'].lower().startswith('undefined'):
                problems.append(f'{code}.{ch}: bad heading {info["heading"]!r}')
            if len(errors) > before:
                problems.append(f'{code}.{ch}: {errors[-1][:110]}')
            if (i + 1) % 40 == 0:
                print(f'  ...{i+1}/{len(ordered)}  ({len(problems)} problems so far)')

        print(f'\ncrawled {len(ordered)} chapters')
        await b.close()

    real = [e for e in errors if 'favicon' not in e]
    if problems:
        print(f'\n{len(problems)} PROBLEMS:')
        for q in problems[:40]: print('  -', q)
    else:
        print('\nno problems found')
    if real and not problems:
        print(f'\n{len(real)} console/page errors:')
        for e in real[:10]: print('  -', e[:150])
    sys.exit(1 if problems else 0)

asyncio.run(main())
