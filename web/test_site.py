import asyncio, json, sys
from playwright.async_api import async_playwright
BASE = 'http://127.0.0.1:8777/'
SHOT = '/home/claude/shots'
import os; os.makedirs(SHOT, exist_ok=True)
fails, errs = [], []

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--no-proxy-server'])
        ctx = await b.new_context(viewport={'width': 390, 'height': 844},
                                  device_scale_factor=2, is_mobile=True,
                                  has_touch=True)
        pg = await ctx.new_page()
        # a stale service-worker cache can hide a data bug; start clean
        await pg.goto(BASE, wait_until='load')
        await pg.evaluate("""async () => {
            const rs = await navigator.serviceWorker.getRegistrations();
            await Promise.all(rs.map(r => r.unregister()));
            const ks = await caches.keys();
            await Promise.all(ks.map(k => caches.delete(k)));
        }""")
        pg.on('console', lambda m: errs.append(f"[{m.type}] {m.text}") if m.type == 'error' else None)
        pg.on('pageerror', lambda e: errs.append(f"[pageerror] {e}"))
        pg.on('requestfailed', lambda r: errs.append(f"[404/fail] {r.url.split('/')[-1]} {r.failure}"))

        async def reset(hash_):
            await pg.evaluate("history.replaceState(null,'','#/_')")
            await pg.goto(BASE + hash_, wait_until='load')
            await pg.wait_for_function(
                "() => document.querySelector('#view') && "
                "!document.querySelector('#view .load')", timeout=15000)
            await pg.wait_for_timeout(250)

        def chk(name, cond, detail=''):
            print(('  ok   ' if cond else '  FAIL ') + name + (f'  {detail}' if detail and not cond else ''))
            if not cond: fails.append(name + ' :: ' + str(detail)[:300])

        # ---------------------------------------------------------- reader
        print('reader')
        await reset('#/Jhn.3')
        chk('heading shows John 3', 'John 3' in await pg.inner_text('h1'),
            await pg.inner_text('h1'))
        nv = await pg.locator('.v').count();        chk('36 verses rendered', nv == 36, nv)
        nw = await pg.locator('.w.grk').count();    chk('Greek words tappable', nw > 300, nw)
        chk('English text present', 'God so loved' in await pg.inner_text('#view'))
        chk('no horizontal scroll',
            await pg.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1'),
            await pg.evaluate('document.documentElement.scrollWidth'))
        tap = await pg.evaluate("""() => {
            let bad=0; document.querySelectorAll('.w,.chip,.ib,.hit').forEach(e=>{
              const r=e.getBoundingClientRect(); if(r.height>0&&r.height<22) bad++;});
            return bad;}""")
        chk('tap targets not tiny', tap == 0, f'{tap} under 22px')
        loaded = await pg.evaluate("""async () => {
            await document.fonts.ready;
            return [...document.fonts].filter(f=>f.status==='loaded').map(f=>f.family+'/'+f.weight);
        }""")
        chk('self-hosted fonts loaded', any('CodexUI' in f for f in loaded), loaded)
        chk('Greek face loaded', any('CodexGrk' in f for f in loaded), loaded)
        await pg.screenshot(path=f'{SHOT}/01-reader.png', full_page=False)

        # ------------------------------------------------------ word study
        print('word study')
        await pg.locator('.w.grk').nth(2).click()
        await pg.wait_for_timeout(900)
        s = await pg.inner_text('#sheet')
        chk('sheet opened', await pg.locator('#sheet.open').count() == 1)
        chk('Strongs number shown', 'G0444' in s, s[:200])
        chk('grammar parsed', 'Noun' in s or 'Function=' in s or 'Case=' in s, s[:300])
        chk('lexicon gloss shown', 'man' in s.lower())
        chk('concordance offered', 'Concordance' in s, s[:400])
        await pg.screenshot(path=f'{SHOT}/02-word.png')

        # ----------------------------------------------------- concordance
        print('concordance')
        await pg.locator('[data-conc]').first.click()
        await pg.wait_for_timeout(800)
        s = await pg.inner_text('#sheet')
        chk('concordance count', 'verses contain this word' in s, s[:300])
        nh = await pg.locator('#sheet .hit').count(); chk('refs listed', nh > 20, nh)
        await pg.screenshot(path=f'{SHOT}/03-conc.png')
        await pg.locator('#sheet .hit').first.click()
        await pg.wait_for_timeout(900)
        chk('ref jump worked', await pg.locator('.v').count() > 0)

        # ------------------------------------------- hebrew + RTL + morphemes
        print('hebrew')
        await reset('#/Gen.12')
        chk('RTL applied', await pg.locator('.orig[dir=rtl]').count() > 0)
        await pg.locator('.w.heb').first.click()
        await pg.wait_for_timeout(900)
        s = await pg.inner_text('#sheet')
        chk('multi-part word split', 'parts' in s.lower(), s[:250])
        chk('prefix Strongs H9001', 'H9001' in s, s[:300])
        await pg.screenshot(path=f'{SHOT}/04-hebrew.png')
        await pg.locator('[data-close]').click(); await pg.wait_for_timeout(300)

        # ------------------------------------------------- place / person / event
        print('context chips')
        for kind, want in [('place', 'Today'), ('person', 'named in'), ('event', 'by scheme')]:
            loc = pg.locator(f'[data-k="{kind}"]')
            if await loc.count() == 0:
                chk(f'{kind} chip present', False, 'none in Gen 12'); continue
            await loc.first.click(); await pg.wait_for_timeout(800)
            s = await pg.inner_text('#sheet')
            chk(f'{kind} sheet', want.lower() in s.lower(), s[:250])
            await pg.screenshot(path=f'{SHOT}/05-{kind}.png')
            await pg.locator('[data-close]').click(); await pg.wait_for_timeout(250)

        print('notes + xrefs')
        await reset('#/Jhn.3')
        await pg.locator('[data-k="note"]').first.click(); await pg.wait_for_timeout(600)
        chk('notes sheet', 'unfoldingword' in (await pg.inner_text('#sheet')).lower())
        await pg.screenshot(path=f'{SHOT}/06-notes.png')
        await pg.locator('[data-close]').click(); await pg.wait_for_timeout(250)
        await pg.locator('[data-k="xref"]').first.click(); await pg.wait_for_timeout(600)
        chk('xref sheet', 'cross-references' in (await pg.inner_text('#sheet')).lower())
        await pg.locator('[data-close]').click(); await pg.wait_for_timeout(250)

        # -------------------------------------------------------- commentary
        print('commentary')
        await reset('#/Jhn.3')
        n = await pg.locator('[data-k="cm"]').count()
        chk('commentary chips present', n > 25, n)
        await pg.locator('[data-k="cm"]').nth(15).click()
        await pg.wait_for_timeout(2500)
        s_ = await pg.inner_text('#sheet')
        chk('commentary sheet', 'commentary on john 3' in s_.lower(), s_[:200])
        chk('Henry present', 'Matthew Henry' in s_, s_[:400])
        chk('attribution of scope', 'on verse' in s_.lower(), s_[:500])
        chk('public-domain statement', 'public domain' in s_.lower())
        ntabs = await pg.locator('[data-cmf]').count()
        chk('source filter offered', ntabs > 2, ntabs)
        await pg.screenshot(path=f'{SHOT}/15-commentary.png')
        # filter to one commentator
        if ntabs > 2:
            await pg.locator('[data-cmf]').nth(1).click(); await pg.wait_for_timeout(1500)
            s2 = await pg.inner_text('#sheet')
            chk('filter narrows the list', len(s2) < len(s_) or 'Nothing from' in s2,
                f'{len(s2)} vs {len(s_)}')
        await pg.locator('[data-close]').click(); await pg.wait_for_timeout(300)
        # chapter-level / book preface
        await reset('#/Gen.1')
        if await pg.locator('[data-k="cmch"]').count():
            await pg.locator('[data-k="cmch"]').click(); await pg.wait_for_timeout(2500)
            s3 = await pg.inner_text('#sheet')
            chk('book preface', 'preface to the book' in s3.lower(), s3[:300])
            await pg.screenshot(path=f'{SHOT}/16-preface.png')
            await pg.locator('[data-close]').click(); await pg.wait_for_timeout(300)
        else:
            chk('chapter commentary entry on Gen 1', False, 'no cmch button')

        # ------------------------------------------- every book, not just my favourites
        print('all 66 books')
        await reset('#/Jhn.3')
        bad = await pg.evaluate("""async () => {
            const b = await (await fetch('data/books.json')).json();
            const out = [];
            for (const [code] of b.books) {
              const nm = b.names[code];
              const label = (nm && (nm[1] || nm[0])) || code;
              if (!label || /undefined|null|^\\s*$/.test(label)) out.push([code, label]);
            }
            return out; }""")
        chk('every book has a usable display name', bad == [], bad)
        # open the three most likely to break and read the heading
        for code, want in [('Job', 'Job'), ('Sng', 'Song'), ('3Jn', 'John')]:
            await reset(f'#/{code}.1')
            h = await pg.inner_text('h1')
            chk(f'{code} heading renders', want.lower() in h.lower()
                and 'undefined' not in h.lower(), h)
        # and the picker must name them all
        await reset('#/Jhn.3')
        await pg.locator('#btnBooks').click(); await pg.wait_for_timeout(500)
        names = await pg.evaluate(
            "[...document.querySelectorAll('[data-book]')].map(e=>e.textContent.trim())")
        chk('picker names all 66 with no undefined', len(names) == 66
            and not any('undefined' in n.lower() for n in names),
            [n for n in names if 'undefined' in n.lower()] or len(names))
        await pg.locator('[data-close]').click(); await pg.wait_for_timeout(300)

        # ------------------------------------------------------------ search
        print('search')
        for tab, q, want in [('verse', 'shepherd', 'verses'),
                             ('word', 'shepherd', 'commonest first'),
                             ('dict', 'shepherd', 'headword'),
                             ('note', 'shepherd', 'verses')]:
            await pg.goto(BASE + '#/search?q=' + q, wait_until='networkidle')
            await pg.wait_for_timeout(400)
            if tab != 'verse':
                await pg.locator(f'[data-tab="{tab}"]').click()
            await pg.wait_for_timeout(1500)
            txt = await pg.inner_text('#results')
            chk(f'search/{tab}', want in txt.lower(), txt[:220])
            await pg.screenshot(path=f'{SHOT}/07-search-{tab}.png')
        await pg.goto(BASE + '#/search?q=john+3:16', wait_until='networkidle')
        await pg.wait_for_timeout(900)
        chk('reference parsed', 'Go to John 3:16' in await pg.inner_text('#results'),
            (await pg.inner_text('#results'))[:200])

        # -------------------------------------------------------- chronology
        print('chronology')
        await reset('#/chrono')
        t = await pg.inner_text('#view')
        chk('chrono loads', 'The story in order' in t)
        chk('dated events listed', await pg.locator('.hit').count() > 100,
            await pg.locator('.hit').count())
        chk('BC years shown', ' BC' in t)
        await pg.screenshot(path=f'{SHOT}/08-chrono.png')
        await pg.locator('[data-setscheme2="ussher"]').click(); await pg.wait_for_timeout(1200)
        t = await pg.inner_text('#view')
        chk('partial-scheme warning', 'only anchors' in t, t[:300])
        await pg.screenshot(path=f'{SHOT}/09-chrono-ussher.png')

        # ----------------------------------------------------------- offline
        print('offline download')
        await reset('#/offline')
        # The clean slate at the top of this run unregistered the worker, and
        # every navigation since has been a hash change, so boot() has not run
        # again. Downloading is only meaningful with the worker in control, so
        # force a real load and wait for it to claim the page.
        await pg.reload(wait_until='load')
        await pg.wait_for_function(
            "() => navigator.serviceWorker.controller != null", timeout=20000)
        await pg.wait_for_timeout(500)
        t = await pg.inner_text('#view')
        chk('offline page loads', 'keep it offline' in t.lower(), t[:200])
        tiers = await pg.locator('[data-tier]').count()
        chk('six tiers offered', tiers == 6, tiers)
        for want in ['The text', 'Word study', 'Search', 'commentators', 'Photographs', 'engravings']:
            chk(f'tier {want}', want.lower() in t.lower())
        chk('a total size is shown', 'MB' in t, t[:200])
        label = await pg.locator('[data-dlstart]').inner_text()
        chk('download button names size and count', 'MB' in label and 'files' in label, label)
        # deselecting a tier must shrink the total
        import re
        def mb(x):
            m = re.search(r'([\d.]+)\s*MB', x)
            return float(m.group(1)) if m else -1
        before = mb(label)
        await pg.locator('[data-tier="commentary"]').click()
        await pg.wait_for_timeout(900)
        after = mb(await pg.locator('[data-dlstart]').inner_text())
        chk('deselecting commentary shrinks the download', after < before,
            f'{after} vs {before}')
        await pg.locator('[data-tier="commentary"]').click()
        await pg.wait_for_timeout(700)
        await pg.screenshot(path=f'{SHOT}/17-offline.png')
        # the real thing: download one tier and confirm it is cached
        for t in ('text', 'commentary', 'study', 'pictures', 'engravings'):
            await pg.locator(f'[data-tier="{t}"]').click()
            await pg.wait_for_timeout(250)
        await pg.wait_for_timeout(900)
        lbl = await pg.locator('[data-dlstart]').inner_text()
        chk('only the search tier left selected', mb(lbl) < 20, lbl)
        await pg.locator('[data-dlstart]').click()
        try:
            await pg.wait_for_function(
                "() => document.querySelector('#view') && "
                "/Done|Finished|Stopped/.test(document.querySelector('#view').textContent)",
                timeout=180000)
            done = await pg.inner_text('#view')
            chk('download reports completion', 'Done' in done or 'Finished' in done,
                done[:200])
        except Exception as e:
            chk('download reports completion', False, str(e)[:200])
        cached = await pg.evaluate("""async () => {
            const ks = await caches.keys(); let n = 0;
            for (const k of ks) { if (k.includes('data')) {
                const c = await caches.open(k); n += (await c.keys()).length; } }
            return n; }""")
        chk('search index actually landed in the cache', cached > 700, cached)
        # and it must still be readable with the network cut
        await ctx.set_offline(True)
        got = await pg.evaluate("""async () => {
            try { const r = await fetch('data/idx/g/aa.json');
                  if (!r.ok) return 'status ' + r.status;
                  const j = await r.json(); return Object.keys(j).length; }
            catch (e) { return 'threw: ' + e.message; } }""")
        chk('a downloaded index reads back offline',
            isinstance(got, (int, float)) and got > 0, got)
        await ctx.set_offline(False)
        await pg.screenshot(path=f'{SHOT}/18-offline-done.png')

        # ------------------------------------------------------------- about
        print('about')
        await reset('#/about')
        t = await pg.inner_text('#view')
        for want in ['Why the dates disagree', 'STEPBible', 'unfoldingWord',
                     'Erasmian', 'Audio', 'MPL-2.0']:
            chk(f'about mentions {want}', want.lower() in t.lower())
        for want in ['bible.db.gz.part', 'commentary.db.gz', 'memory stick', 'gunzip']:
            chk(f'about offers {want}', want.lower() in t.lower())
        links = await pg.evaluate(
            "[...document.querySelectorAll('#view a[href^=\"download/\"]')].map(a=>a.getAttribute('href'))")
        chk('download links present', len(links) >= 2, links)
        for href in links:
            r = await pg.request.head(BASE + href)
            chk(f'{href} is served', r.status in (200, 206), r.status)
        await pg.screenshot(path=f'{SHOT}/10-about.png', full_page=True)

        # ---------------------------------------------------------- settings
        print('settings')
        await reset('#/Jhn.3')
        await pg.locator('#btnSet').click(); await pg.wait_for_timeout(400)
        chk('settings sheet', 'greek pronunciation' in (await pg.inner_text('#sheet')).lower())
        await pg.locator('[data-settx="YLT"]').click(); await pg.wait_for_timeout(700)
        chk('translation switched', "Young's Literal" in await pg.inner_text('#view'),
            (await pg.inner_text('#view'))[:200])
        await pg.locator('[data-setpron="modern"]').click(); await pg.wait_for_timeout(600)
        chk('pronunciation note', 'Modern Greek' in await pg.inner_text('#sheet'))
        await pg.screenshot(path=f'{SHOT}/11-settings.png')

        # --------------------------------------------------------- navigation
        print('navigation')
        await pg.locator('[data-close]').click(); await pg.wait_for_timeout(400)
        await pg.locator('#btnBooks').click(); await pg.wait_for_timeout(400)
        nb = await pg.locator('[data-book]').count(); chk('66 books listed', nb == 66, nb)
        await pg.locator('[data-book="Psa"]').click(); await pg.wait_for_timeout(400)
        nc = await pg.locator('[data-ch]').count(); chk('150 psalms', nc == 150, nc)
        await pg.locator('[data-ch="23"]').click(); await pg.wait_for_timeout(1200)
        chk('Psalm 23 opens', 'Psalms 23' in await pg.inner_text('h1'),
            await pg.inner_text('h1'))
        await pg.screenshot(path=f'{SHOT}/12-psalm23.png')

        # ------------------------------------------------------------ offline
        print('offline (service worker)')
        # The honest test is a first-time visitor in a clean profile who then
        # loses signal — not a browser that has already warmed every cache.
        ctx_o = await b.new_context(viewport={'width': 390, 'height': 844},
                                    device_scale_factor=2, is_mobile=True,
                                    has_touch=True)
        pg_o = await ctx_o.new_page()
        await pg_o.goto(BASE + '#/Jhn.3', wait_until='load')
        await pg_o.wait_for_timeout(4000)
        st = await pg_o.evaluate("""async () => {
            const reg = await navigator.serviceWorker.getRegistration();
            const ks = await caches.keys(); const out = {reg: !!reg, ch: false, n: 0};
            for (const k of ks) { const c = await caches.open(k);
              out.n += (await c.keys()).length;
              if (await c.match('/data/ch/Jhn.3.json')) out.ch = true; }
            return out; }""")
        chk('service worker registered', st['reg'], st)
        chk('first visit caches the chapter being read', st['ch'], st)
        await ctx_o.set_offline(True)
        await pg_o.reload(wait_until='domcontentloaded')
        await pg_o.wait_for_timeout(3000)
        t = await pg_o.inner_text('#view')
        chk('offline reload after one visit shows the chapter',
            'Pharisees' in t and 'John 3' in t, t[:200])
        # a word tap must still work offline
        try:
            await pg_o.locator('.w.grk').nth(2).click(timeout=8000)
            await pg_o.wait_for_timeout(1500)
            sw_ = await pg_o.inner_text('#sheet')
            chk('word study works offline', 'G0444' in sw_, sw_[:160])
            # it must not claim the word has no lexicon entry when it
            # simply could not fetch one
            chk('offline lexicon gap stated honestly',
                'has not been downloaded' in sw_ or 'man' in sw_.lower(),
                sw_[:300])
            chk('no false "no entry" claim offline',
                'No lexicon entry under this number' not in sw_, sw_[:300])
        except Exception as e:
            chk('word study works offline', False, str(e)[:160])
        await pg_o.screenshot(path=f'{SHOT}/13-offline.png')
        await ctx_o.set_offline(False)
        await ctx_o.close()

        # ------------------------------------------------------- dark mode
        await ctx.close()
        ctx2 = await b.new_context(viewport={'width': 390, 'height': 844},
                                   device_scale_factor=2, is_mobile=True,
                                   has_touch=True, color_scheme='dark')
        pg2 = await ctx2.new_page()
        await pg2.goto(BASE + '#/Jhn.3', wait_until='networkidle'); await pg2.wait_for_timeout(900)
        await pg2.evaluate("document.documentElement.setAttribute('data-theme','dark')")
        await pg2.wait_for_timeout(300)
        bg = await pg2.evaluate("getComputedStyle(document.body).backgroundColor")
        chk('the dark palette renders', bg != 'rgb(248, 247, 244)', bg)
        await pg2.screenshot(path=f'{SHOT}/14-dark.png')
        await b.close()

    print()
    real = [e for e in errs if 'favicon' not in e and 'fonts.g' not in e]
    if real:
        print(f'CONSOLE / NETWORK ISSUES ({len(real)}):')
        for e in real[:25]: print('  ', e[:220])
    print(f"\n{'ALL CHECKS PASSED' if not fails else str(len(fails))+' FAILURES'}")
    for f in fails: print('  -', f)
    sys.exit(1 if fails else 0)

asyncio.run(main())
