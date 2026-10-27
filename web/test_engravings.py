"""Dore's engravings: that they appear where the text puts them, once each,
are credited, and can be turned off."""
import asyncio, json, sys
from playwright.async_api import async_playwright
BASE='http://127.0.0.1:8777/'; SHOT='/home/claude/shots'

async def main():
    fails=[]
    def chk(n,c,d=''):
        print(('  ok   ' if c else '  FAIL ')+n+(f'  {d}' if not c else ''))
        if not c: fails.append(f'{n} :: {d}')

    d = json.load(open('/home/claude/site/data/dore.json', encoding='utf-8'))
    print(f"{len(d['plates'])} plates, shown at {len(d['at'])} verses")
    chk('every plate has a title', all(p.get('title') for p in d['plates'].values()))
    chk('every plate links to its source', all(p.get('page') for p in d['plates'].values()))
    chk('every plate is public domain',
        all('ublic domain' in (p.get('licence') or '') for p in d['plates'].values()),
        sorted({p.get('licence') for p in d['plates'].values()}))
    seen = [pid for ps in d['at'].values() for pid in ps]
    chk('no plate is placed twice', len(seen) == len(set(seen)),
        len(seen) - len(set(seen)))
    import os
    missing = [p['file'] for p in d['plates'].values()
               if not os.path.exists('/home/claude/site/data/dore/' + p['file'])]
    chk('every plate file exists', not missing, missing[:4])

    async with async_playwright() as p:
        b=await p.chromium.launch(args=['--no-proxy-server'])
        ctx=await b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
        pg=await ctx.new_page()
        bad=[]
        pg.on('response', lambda r: bad.append(f'{r.status} {r.url.split("/")[-1]}')
              if '/dore/' in r.url and r.status >= 400 else None)

        async def chapter(ref):
            await pg.goto(BASE+f'#/{ref}', wait_until='load')
            await pg.wait_for_function(
                "() => document.querySelector('#view') && !document.querySelector('#view .load')",
                timeout=20000)
            await pg.wait_for_timeout(900)

        print('\nGenesis 1 - the Creation')
        await chapter('Gen.1')
        n = await pg.locator('.plate').count()
        chk('an engraving is set in the chapter', n >= 1, n)
        if n:
            ok = await pg.evaluate("""() => { const i=document.querySelector('.plate img');
                return i.complete && i.naturalWidth > 100; }""")
            chk('it actually loaded', ok)
            cap = await pg.locator('.plate figcaption').first.inner_text()
            chk('it is credited to Dore and dated', 'Dor' in cap and '1866' in cap, cap[:90])
            chk('the reference is shown', ':' in cap, cap[:90])
            alt = await pg.locator('.plate img').first.get_attribute('alt')
            chk('it has alt text naming the artist', alt and 'Dor' in alt, alt)
            # it must sit inside the reading column, not overflow
            over = await pg.evaluate("document.documentElement.scrollWidth - window.innerWidth")
            chk('no sideways overflow', over <= 1, over)
            await pg.screenshot(path=f'{SHOT}/23-dore-gen1.png')

        print('\nJudges 16 - Samson, the plates my first pass threw away')
        await chapter('Jdg.16')
        n = await pg.locator('.plate').count()
        chk('the Judges plates are placed', n >= 1, n)
        if n:
            caps = await pg.locator('.plate figcaption').all_inner_texts()
            chk('Samson is among them', any('samson' in c.lower() for c in caps), caps[:3])
            await pg.screenshot(path=f'{SHOT}/24-dore-judges.png')

        print('\nturning them off')
        await pg.locator('#btnAa').click(); await pg.wait_for_timeout(500)
        chk('a switch is offered', await pg.locator('[data-setpix]').count() == 1)
        await pg.locator('[data-setpix]').click(); await pg.wait_for_timeout(800)
        await pg.evaluate("document.querySelector('[data-close]')?.click()")
        await pg.wait_for_timeout(400)
        n2 = await pg.locator('.plate').count()
        chk('the engravings go away', n2 == 0, n2)
        await pg.reload(wait_until='load'); await pg.wait_for_timeout(2500)
        n3 = await pg.locator('.plate').count()
        chk('and stay away after a reload', n3 == 0, n3)
        # and the text is untouched
        nv = await pg.locator('.v').count()
        chk('the chapter still reads normally', nv > 10, nv)

        chk('no engraving request failed', not bad, bad[:4])
        await b.close()
    print()
    print('ALL CHECKS PASSED' if not fails else f'{len(fails)} FAILURES')
    for f in fails: print('  -', f)
    sys.exit(1 if fails else 0)
asyncio.run(main())
