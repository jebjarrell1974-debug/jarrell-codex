"""The photographs: that they load, that they are credited, and that the
honest cases stay honest."""
import asyncio, json, sys
from playwright.async_api import async_playwright
BASE='http://127.0.0.1:8777/'; SHOT='/home/claude/shots'

async def main():
    fails=[]
    def chk(n,c,d=''):
        print(('  ok   ' if c else '  FAIL ')+n+(f'  {d}' if not c else ''))
        if not c: fails.append(f'{n} :: {d}')
    async with async_playwright() as p:
        b=await p.chromium.launch(args=['--no-proxy-server'])
        ctx=await b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
        pg=await ctx.new_page()
        bad=[]
        pg.on('requestfailed', lambda r: bad.append(r.url) if '/pix/' in r.url else None)
        pg.on('response', lambda r: bad.append(f'{r.status} {r.url}')
              if '/pix/' in r.url and r.status >= 400 else None)

        man = json.load(open('/home/claude/site/data/pix_manifest.json', encoding='utf-8'))
        print(f'{len(man)} photographs in the manifest')
        chk('every picture names a licence',
            all(m.get('licence') for m in man.values()),
            [k for k,m in man.items() if not m.get('licence')][:4])

        # The point of CC BY, CC BY-SA and GPL is that you name the author.
        # Fourteen of these shipped with a licence and artist: null, which
        # showed the terms with nobody to credit. A manifest entry under an
        # attribution licence and without a credit must fail here rather
        # than reach a reader.
        def txt(m, k):
            v = m.get(k)
            return v if isinstance(v, str) else ''
        def public(m):
            lic = (txt(m, 'licence') + ' ' + txt(m, 'licurl')).lower()
            return ('publicdomain' in lic or 'public domain' in lic
                    or 'cc0' in lic)
        owed = [k for k, m in man.items()
                if not public(m) and not txt(m, 'artist')]
        chk('every picture under an attribution licence names its author',
            not owed, owed[:6])
        nolink = [k for k, m in man.items() if not txt(m, 'page')]
        chk('and links the page it came from', not nolink, nolink[:6])
        chk('every picture links back to its source',
            all(m.get('page') for m in man.values()))
        chk('nothing is over 300 KB',
            max(m['bytes'] for m in man.values()) <= 307200,
            max(m['bytes'] for m in man.values()))

        # a located, identified place: Nazareth is in Luke 2
        async def open_place(ref, want):
            await pg.goto(BASE+f'#/{ref}', wait_until='load')
            await pg.wait_for_function(
                "() => document.querySelector('#view') && !document.querySelector('#view .load')",
                timeout=20000)
            n = await pg.locator('[data-k="place"]').count()
            if not n: return None
            for i in range(n):
                el = pg.locator('[data-k="place"]').nth(i)
                if want.lower() in (await el.inner_text()).lower():
                    await el.click(); await pg.wait_for_timeout(1500)
                    return await pg.inner_text('#sheet')
            return None

        # ---- the second place a reader taps ----------------------------
        # This is the one that was broken on the live site. lazy.pix()
        # returned the cached object rather than a promise on every call
        # after the first, so .catch threw, placeSheet threw with it, and
        # the panel kept whatever had been in it before - the previous
        # place's photograph, under the new place's name. Every test only
        # ever opened one place, so nothing said a word.
        print('\nopening one place after another')
        first = await open_place('Luk.2', 'Nazareth')
        chk('the first place opens', first is not None)
        second = await open_place('Act.9', 'Damascus')
        chk('and so does the second', second is not None)
        if second:
            chk('the second shows its own name, not the first one\'s',
                'Damascus' in second and 'Nazareth' not in second,
                second[:160])
        third = await open_place('Mat.2', 'Jerusalem')
        chk('and a third', third is not None and 'Jerusalem' in (third or ''),
            (third or '')[:120])

        print('\na place with a photograph')
        txt = await open_place('Luk.2', 'Nazareth')
        chk('found Nazareth', txt is not None)
        if txt:
            n_img = await pg.locator('#sheet figure img').count()
            chk('a photograph is shown', n_img == 1, n_img)
            if n_img:
                ok = await pg.evaluate("""() => { const i=document.querySelector('#sheet figure img');
                    return i.complete && i.naturalWidth > 100; }""")
                chk('the photograph actually loaded', ok)
                alt = await pg.locator('#sheet figure img').get_attribute('alt')
                chk('it has alt text', alt and len(alt) > 5, alt)
                cap = await pg.locator('#sheet figcaption').inner_text()
                chk('the credit is visible', len(cap) > 5, cap)
            chk('map, satellite and street level are offered',
                'stand there' in txt.lower() and 'from above' in txt.lower(), txt[:200])
            await pg.screenshot(path=f'{SHOT}/21-place-photo.png')

        print('\na disputed place must say the photo is of one candidate')
        found_disputed = False
        for ref, want in [('Mat.4', 'Capernaum'), ('Jos.6', 'Jericho'), ('Gen.12', 'Shechem')]:
            t = await open_place(ref, want)
            if not t: continue
            if 'proposed' in t.lower() or 'disputed' in t.lower():
                has_img = await pg.locator('#sheet figure img').count()
                if has_img:
                    chk(f'{want}: the caption flags one proposed site',
                        'one' in (await pg.locator('#sheet figcaption').inner_text()).lower(),
                        await pg.locator('#sheet figcaption').inner_text())
                    found_disputed = True
                    await pg.screenshot(path=f'{SHOT}/22-disputed-photo.png')
                    break
        if not found_disputed:
            print('       (no disputed place with a photo in the chapters tried)')

        print('\na place with no photograph')
        shown = False
        await pg.goto(BASE+'#/Gen.2', wait_until='load'); await pg.wait_for_timeout(1800)
        n = await pg.locator('[data-k="place"]').count()
        for i in range(min(n, 6)):
            await pg.locator('[data-k="place"]').nth(i).click(); await pg.wait_for_timeout(1200)
            if await pg.locator('#sheet figure img').count() == 0:
                t = await pg.inner_text('#sheet')
                chk('it still renders without inventing a picture', len(t) > 60, t[:120])
                shown = True
                await pg.evaluate("document.querySelector('[data-close]')?.click()")
                break
            await pg.evaluate("document.querySelector('[data-close]')?.click()")
            await pg.wait_for_timeout(300)
        if not shown: print('       (every place tried had a photo)')

        chk('no picture request failed', not bad, bad[:4])
        await b.close()
    print()
    print('ALL CHECKS PASSED' if not fails else f'{len(fails)} FAILURES')
    for f in fails: print('  -', f)
    sys.exit(1 if fails else 0)
asyncio.run(main())
