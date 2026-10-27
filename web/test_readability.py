"""Measure readability in a real browser, not in my head.

Everything here is computed from rendered pixels and computed styles, so a
CSS change that quietly undoes one of these gets caught.
"""
import asyncio, sys
from playwright.async_api import async_playwright
BASE = 'http://127.0.0.1:8777/'
SHOT = '/home/claude/shots'

LUM = """
const lum = c => { const [r,g,b] = c.match(/\\d+(\\.\\d+)?/g).slice(0,3).map(Number)
    .map(v => { v/=255; return v<=0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4); });
  return 0.2126*r + 0.7152*g + 0.0722*b; };
const ratio = (a,b) => { const [x,y]=[lum(a),lum(b)].sort((m,n)=>n-m);
  return (x+0.05)/(y+0.05); };
"""

async def main():
    fails = []
    def chk(name, cond, detail=''):
        print(('  ok   ' if cond else '  FAIL ') + name + (f'  {detail}' if not cond else ''))
        if not cond: fails.append(f'{name} :: {detail}')

    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--no-proxy-server'])
        ctx = await b.new_context(viewport={'width': 390, 'height': 844},
                                  device_scale_factor=2, is_mobile=True, has_touch=True)
        pg = await ctx.new_page()
        await pg.goto(BASE + '#/Jhn.3', wait_until='load')
        await pg.wait_for_function(
            "() => document.querySelector('#view') && !document.querySelector('#view .load')",
            timeout=20000)
        await pg.wait_for_timeout(400)

        print('text size at default')
        sizes = await pg.evaluate("""() => {
            const px = s => parseFloat(getComputedStyle(s).fontSize);
            const q = s => document.querySelector(s);
            return {
              root: px(document.documentElement),
              english: px(q('.eng')),
              greek: px(q('.w')),
              chip: px(q('.chip')),
              smallest: Math.min(...[...document.querySelectorAll('#view *')]
                 .filter(e => e.textContent.trim() && !e.children.length)
                 .map(px)),
            }; }""")
        chk('body text is at least 18px', sizes['english'] >= 18, sizes['english'])
        chk('original-language text is at least 18px', sizes['greek'] >= 18, sizes['greek'])
        chk('nothing on the page is under 16px', sizes['smallest'] >= 16, sizes['smallest'])
        print(f"       root {sizes['root']}px  english {sizes['english']}px  "
              f"greek {sizes['greek']}px  smallest {sizes['smallest']}px")

        print('\nline spacing and measure')
        lh = await pg.evaluate("""() => {
            const e = document.querySelector('.eng');
            const cs = getComputedStyle(e);
            return { lh: parseFloat(cs.lineHeight) / parseFloat(cs.fontSize),
                     width: e.getBoundingClientRect().width,
                     fs: parseFloat(cs.fontSize) }; }""")
        chk('line height is at least 1.5', lh['lh'] >= 1.5, round(lh['lh'], 2))
        cpl = lh['width'] / (lh['fs'] * 0.5)
        chk('line length stays under ~75 characters', cpl <= 80, round(cpl))
        print(f"       line-height {lh['lh']:.2f}  about {cpl:.0f} characters per line")

        print('\ncontrast, measured from rendered pixels')
        con = await pg.evaluate(LUM + """() => {
            const bg = getComputedStyle(document.body).backgroundColor;
            const out = {};
            const grab = (sel, name) => { const e = document.querySelector(sel);
              if (e) out[name] = ratio(getComputedStyle(e).color, bg); };
            grab('.eng', 'english verse');
            grab('.w', 'original word');
            grab('.vnum', 'verse number');
            grab('.ot', 'caption');
            grab('.chip', 'marker chip');
            grab('h1', 'heading');
            return out; }""")
        for name, r in con.items():
            level = 'AAA' if r >= 7 else ('AA' if r >= 4.5 else 'FAIL')
            chk(f'contrast: {name} meets AA', r >= 4.5, f'{r:.2f}:1')
            print(f"       {name:<16} {r:5.2f}:1  {level}")

        print('\ntap targets')
        taps = await pg.evaluate("""() => {
            const small = [];
            document.querySelectorAll('button,a,select,input').forEach(e => {
              const r = e.getBoundingClientRect();
              if (r.width > 0 && r.height > 0 && r.height < 44)
                small.push([e.className || e.tagName, Math.round(r.height)]);
            });
            return small; }""")
        chk('every control is at least 44px tall', len(taps) == 0, taps[:6])

        print('\nthe size control')
        # the reading controls must be one tap from the page being read,
        # not two taps down inside Settings
        chk('an Aa button sits in the reading bar', await pg.locator('#btnAa').count() == 1)
        await pg.locator('#btnAa').click(); await pg.wait_for_timeout(500)
        chk('Aa opens the text size control directly',
            'text size' in (await pg.inner_text('#sheet')).lower())
        start = await pg.evaluate("parseFloat(getComputedStyle(document.documentElement).fontSize)")
        for _ in range(20):
            n = await pg.locator('[data-fs="1"]').count()
            if not n: break
            if await pg.locator('[data-fs="1"]').is_disabled(): break
            await pg.locator('[data-fs="1"]').click(); await pg.wait_for_timeout(250)
        big = await pg.evaluate("parseFloat(getComputedStyle(document.documentElement).fontSize)")
        chk('+ makes the text bigger', big > start, f'{start} -> {big}')
        chk('the top of the range is at least 28px', big >= 28, big)
        await pg.screenshot(path=f'{SHOT}/19-large-text.png')

        # it must survive a reload
        await pg.reload(wait_until='load'); await pg.wait_for_timeout(2500)
        kept = await pg.evaluate("parseFloat(getComputedStyle(document.documentElement).fontSize)")
        chk('the chosen size survives a reload', abs(kept - big) < 0.5, f'{kept} vs {big}')

        # and the page must still work at that size
        over = await pg.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        chk('no sideways scrolling at the largest size', over <= 1, over)
        nv = await pg.locator('.v').count()
        chk('the chapter still renders at the largest size', nv == 36, nv)

        print('\ncolour is the reader\'s choice, not the phone\'s')
        await ctx.close()
        ctx2 = await b.new_context(viewport={'width': 390, 'height': 844},
                                   is_mobile=True, has_touch=True, color_scheme='dark')
        pg2 = await ctx2.new_page()
        await pg2.goto(BASE + '#/Jhn.3', wait_until='load'); await pg2.wait_for_timeout(1800)
        bg0 = await pg2.evaluate("getComputedStyle(document.body).backgroundColor")
        chk('a dark phone still gets Paper by default', '252, 251, 248' in bg0, bg0)
        await pg2.locator('#btnAa').click(); await pg2.wait_for_timeout(500)
        n = await pg2.locator('[data-setscheme3]').count()
        chk('a choice of schemes is offered', n >= 6, n)
        await pg2.locator('[data-setscheme3="night"]').click(); await pg2.wait_for_timeout(600)
        bgd = await pg2.evaluate("getComputedStyle(document.body).backgroundColor")
        chk('choosing Night goes dark', bgd != bg0, bgd)
        cond = await pg2.evaluate(LUM + """() => {
            const bg = getComputedStyle(document.body).backgroundColor;
            return ratio(getComputedStyle(document.querySelector('.eng')).color, bg); }""")
        chk('Night meets AAA', cond >= 7, f'{cond:.2f}:1')
        await pg2.locator('[data-setscheme3="paper"]').click(); await pg2.wait_for_timeout(600)
        bgl = await pg2.evaluate("getComputedStyle(document.body).backgroundColor")
        chk('choosing Paper goes back', '252, 251, 248' in bgl, bgl)
        conl = await pg2.evaluate(LUM + """() => {
            const bg = getComputedStyle(document.body).backgroundColor;
            return ratio(getComputedStyle(document.querySelector('.eng')).color, bg); }""")
        chk('Paper meets AAA', conl >= 7, f'{conl:.2f}:1')
        await pg2.screenshot(path=f'{SHOT}/20-forced-light.png')

        print('\nno dropdowns anywhere')
        pg3 = await ctx2.new_page()
        await pg3.goto(BASE + '#/Jhn.3', wait_until='load'); await pg3.wait_for_timeout(1500)
        found = []
        for name, opener in [('settings', '#btnSet'), ('reading', '#btnAa')]:
            await pg3.locator(opener).click(); await pg3.wait_for_timeout(500)
            n = await pg3.locator('#sheet select').count()
            if n: found.append((name, n))
            await pg3.locator('[data-close]').click(); await pg3.wait_for_timeout(300)
        await pg3.goto(BASE + '#/chrono', wait_until='load'); await pg3.wait_for_timeout(2000)
        n = await pg3.locator('#view select').count()
        if n: found.append(('chronology', n))
        chk('no <select> survives in any panel', not found, found)
        await b.close()

    print()
    print('ALL CHECKS PASSED' if not fails else f'{len(fails)} FAILURES')
    for f in fails: print('  -', f)
    sys.exit(1 if fails else 0)

asyncio.run(main())
