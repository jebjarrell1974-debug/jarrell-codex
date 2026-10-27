"""Every colour scheme, measured from rendered pixels in each one.

The generator checks the tokens. This checks what the browser actually
paints, which is the only thing a reader sees.
"""
import asyncio, json, sys
from playwright.async_api import async_playwright
BASE='http://127.0.0.1:8777/'; SHOT='/home/claude/shots'

LUM = """
const lum = c => { const [r,g,b] = c.match(/\\d+(\\.\\d+)?/g).slice(0,3).map(Number)
    .map(v => { v/=255; return v<=0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4); });
  return 0.2126*r + 0.7152*g + 0.0722*b; };
const ratio = (a,b) => { const [x,y]=[lum(a),lum(b)].sort((m,n)=>n-m);
  return (x+0.05)/(y+0.05); };
"""

async def main():
    fails=[]
    def chk(n,c,d=''):
        print(('  ok   ' if c else '  FAIL ')+n+(f'  {d}' if not c else ''))
        if not c: fails.append(f'{n} :: {d}')

    schemes = json.load(open('/home/claude/site/data/schemes.json', encoding='utf-8'))
    async with async_playwright() as p:
        b=await p.chromium.launch(args=['--no-proxy-server'])
        ctx=await b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
        pg=await ctx.new_page()
        await pg.goto(BASE+'#/Jhn.3', wait_until='load')
        await pg.wait_for_function(
            "() => document.querySelector('#view') && !document.querySelector('#view .load')",
            timeout=20000)

        await pg.locator('#btnAa').click(); await pg.wait_for_timeout(500)
        n = await pg.locator('[data-setscheme3]').count()
        chk('seven choices offered (six schemes plus follow-the-phone)', n == 7, n)
        await pg.evaluate("document.querySelector('[data-close]')?.click()")
        await pg.wait_for_timeout(300)

        for key, meta in schemes.items():
            print(f"\n{meta['name']}  (bg {meta['paper']})")
            await pg.evaluate(f"document.documentElement.setAttribute('data-scheme','{key}')")
            await pg.wait_for_timeout(250)
            got = await pg.evaluate(LUM + """() => {
                const bg = getComputedStyle(document.body).backgroundColor;
                const out = {bg};
                const g = (sel,name) => { const e=document.querySelector(sel);
                  if (e) out[name] = ratio(getComputedStyle(e).color, bg); };
                g('.eng','english verse'); g('.w','original word');
                g('.vnum','verse number'); g('.ot','caption');
                g('h1','heading'); g('.chip','marker');
                g('.chip.cm','commentary marker'); g('.chip.xr','cross-ref marker');
                return out; }""")
            bg = got.pop('bg')
            for name, r in got.items():
                lvl = 'AAA' if r>=7 else ('AA' if r>=4.5 else 'FAIL')
                chk(f'{key}: {name} clears 7:1', r>=7, f'{r:.2f}:1')
                print(f"       {name:<20} {r:5.2f}:1  {lvl}")
            await pg.screenshot(path=f'{SHOT}/scheme-{key}.png')

        print('\nthe choice sticks')
        await pg.locator('#btnAa').click(); await pg.wait_for_timeout(400)
        await pg.locator('[data-setscheme3="sepia"]').click(); await pg.wait_for_timeout(600)
        bg1 = await pg.evaluate("getComputedStyle(document.body).backgroundColor")
        chk('choosing Sepia applies it', '244, 236, 216' in bg1, bg1)
        await pg.reload(wait_until='load'); await pg.wait_for_timeout(2500)
        bg2 = await pg.evaluate("getComputedStyle(document.body).backgroundColor")
        chk('and survives a reload', bg2 == bg1, f'{bg2} vs {bg1}')
        tc = await pg.evaluate(
            "document.querySelector('meta[name=theme-color]')?.getAttribute('content')")
        chk('the browser chrome follows the scheme', (tc or '').upper() == '#F4ECD8', tc)
        await b.close()
    print()
    print('ALL CHECKS PASSED' if not fails else f'{len(fails)} FAILURES')
    for f in fails: print('  -', f)
    sys.exit(1 if fails else 0)
asyncio.run(main())
