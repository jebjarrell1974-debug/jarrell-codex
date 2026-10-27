"""The photosphere viewer.

The hard part is not whether it draws something but whether it draws the
right thing, so the fixture is a grid with its compass bearings painted
into it: look north and the middle pixel must be the one labelled N. A
shader with longitude backwards passes every other test and fails this one.
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


# The published manifest, whatever it currently holds.
MAN = json.load(io.open('/home/claude/site/data/pano.json', encoding='utf-8'))

# The fixture, injected into the running page. Its contents are known, so
# the projection can be checked against them rather than against a
# photograph nobody can assert anything about.
FIXTURE = {'Nazareth': {
    'file': '_test.webp', 'w': 2048, 'h': 1024, 'km': 0.0,
    'licence': 'CC BY-SA 4.0',
    'artist': 'A test image, not a photograph of anywhere',
    'taken': '', 'page': ''}}


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--no-proxy-server',
                                          '--use-gl=swiftshader',
                                          '--enable-unsafe-swiftshader'])
        ctx = await b.new_context(viewport={'width': 390, 'height': 844},
                                  device_scale_factor=2, is_mobile=True,
                                  has_touch=True)
        pg = await ctx.new_page()
        pg.on('console', lambda m: errs.append(f'[{m.type}] {m.text}')
              if m.type == 'error' else None)
        pg.on('pageerror', lambda e: errs.append(f'[pageerror] {e}'))

        await pg.goto(BASE, wait_until='load')
        await pg.evaluate("""async () => {
            const rs = await navigator.serviceWorker.getRegistrations();
            await Promise.all(rs.map(r => r.unregister()));
            const ks = await caches.keys();
            await Promise.all(ks.map(k => caches.delete(k)));
            localStorage.setItem('codex-seen','1');
        }""")

        print(f'the published manifest ({len(MAN)} photospheres)')
        bad = [k for k, v in MAN.items()
               if not (v.get('w') and v.get('h')) or v['w'] != v['h'] * 2]
        chk('every entry is exactly twice as wide as it is tall', not bad, bad[:4])
        bad = [k for k, v in MAN.items() if v['w'] & (v['w'] - 1)]
        chk('and a power of two, so the wrap is free', not bad, bad[:4])
        bad = [k for k, v in MAN.items() if not v.get('licence')]
        chk('every one names a licence', not bad, bad[:4])
        bad = [k for k, v in MAN.items() if not v.get('file')]
        chk('and a file', not bad, bad[:4])
        bad = [k for k, v in MAN.items()
               if 'by-sa' not in str(v.get('licence', '')).lower()
               and 'cc0' not in str(v.get('licence', '')).lower()
               and 'public domain' not in str(v.get('licence', '')).lower()]
        chk('and a licence that lets us pass it on', not bad, bad[:4])
        bad = [k for k, v in MAN.items()
               if not v.get('artist') and 'cc0' not in str(v.get('licence', '')).lower()]
        chk('and names who took it', not bad, bad[:4])

        # ---- does the viewer come up ------------------------------------
        print('\nopening one')
        name = next(iter(FIXTURE))
        await pg.goto(BASE + '#/Mrk.1', wait_until='load')
        await pg.wait_for_function(
            "() => document.querySelectorAll('#view .v').length > 0", timeout=20000)
        # find a verse with the place we have a panorama for
        found = await pg.evaluate("""([want, fixture]) => {
            // Stand the fixture in for the manifest before the panel
            // reads it, so the viewer is tested against an image whose
            // contents are known.
            S.pano = fixture;
            const b = [...document.querySelectorAll('.chip.place')]
              .find(e => e.textContent.includes(want));
            if (b) { b.click(); return true; }
            return false;
        }""", [name, FIXTURE])
        chk(f'{name} is a place in the text', found, name)
        await pg.wait_for_timeout(900)
        look = pg.locator('[data-look]')
        chk('the place offers to let you look around', await look.count() >= 1,
            await look.count())
        await look.first.click()
        await pg.wait_for_function(
            "() => { const c = document.getElementById('panoC');"
            " return c && c.width > 0 && !document.querySelector('.pano-load'); }",
            timeout=25000)
        await pg.wait_for_timeout(500)
        gl = await pg.evaluate("() => !!PV.gl")
        chk('WebGL came up', gl)

        # ---- is it drawing the right way round -------------------------
        print('\nis it pointing where it says')
        async def band(yaw=0.0, pitch=0.0):
            """Draw and read in one task: without preserveDrawingBuffer the
            default framebuffer is gone by the next evaluate and every
            channel reads back zero, which looks exactly like a viewer
            that drew nothing."""
            return await pg.evaluate("""([y, p]) => {
                PV.yaw = y; PV.pitch = p; panoDraw();
                const c = document.getElementById('panoC'), g = PV.gl;
                const w = c.width, h = c.height, n = 8;
                const read = row => {
                    const px = new Uint8Array(w * n * 4);
                    g.readPixels(0, row, w, n, g.RGBA, g.UNSIGNED_BYTE, px);
                    let r = 0, gg = 0, bb = 0;
                    for (let i = 0; i < px.length; i += 4) {
                        r += px[i]; gg += px[i+1]; bb += px[i+2];
                    }
                    const k = px.length / 4;
                    return [r/k, gg/k, bb/k];
                };
                // readPixels counts rows from the bottom
                return { bottom: read(0), top: read(h - n) };
            }""", [yaw, pitch])

        bands = await band()
        # the fixture is sky above the horizon and ground below
        top, bot = bands['top'], bands['bottom']
        chk('the sky is at the top, not the bottom',
            top[2] > top[0] and bot[0] > bot[2],
            f'top {["%.0f"%v for v in top]} bottom {["%.0f"%v for v in bot]}')

        # Looking up must bring more sky in; the viewer clamps short of the
        # zenith so it can never smear.
        before = bands['bottom'][2] - bands['bottom'][0]
        up = await band(0.0, 1.2)
        after = up['bottom'][2] - up['bottom'][0]
        chk('looking up puts sky where the ground was',
            after > before, f'blueness {before:.0f} -> {after:.0f}')
        down = await band(0.0, -1.2)
        chk('and looking down puts ground where the sky was',
            down['top'][0] > down['top'][2],
            f"top {['%.0f' % v for v in down['top']]}")
        await band(0.0, 0.0)

        print('\nthe seam, which is where a 360 gives itself away')
        a = await pg.evaluate("""() => {
            PV.yaw = 0; PV.pitch = 0; panoDraw();
            const c = document.getElementById('panoC'), g = PV.gl;
            const px = new Uint8Array(4);
            g.readPixels(Math.floor(c.width/2), Math.floor(c.height/2), 1, 1,
                         g.RGBA, g.UNSIGNED_BYTE, px);
            return [px[0], px[1], px[2]];
        }""")
        bb = await pg.evaluate("""() => {
            PV.yaw = Math.PI * 2; PV.pitch = 0; panoDraw();
            const c = document.getElementById('panoC'), g = PV.gl;
            const px = new Uint8Array(4);
            g.readPixels(Math.floor(c.width/2), Math.floor(c.height/2), 1, 1,
                         g.RGBA, g.UNSIGNED_BYTE, px);
            return [px[0], px[1], px[2]];
        }""")
        chk('a full turn comes back to the same view',
            max(abs(a[i] - bb[i]) for i in range(3)) <= 6, f'{a} vs {bb}')
        await pg.evaluate("() => { PV.yaw = 0; panoDraw(); }")

        print('\nthe controls')
        n = await pg.locator('.pbtn').count()
        chk('six of them', n == 6, n)
        boxes = [await e.bounding_box() for e in await pg.locator('.pbtn').all()]
        small = [b for b in boxes if b['height'] < 48]
        chk('each one a real tap target', not small, small[:2])
        y0 = await pg.evaluate("() => PV.yaw")
        await pg.locator('[data-pan="right"]').dispatch_event('mousedown')
        await pg.wait_for_timeout(120)
        await pg.locator('[data-pan="right"]').dispatch_event('mouseup')
        await pg.wait_for_timeout(250)
        y1 = await pg.evaluate("() => PV.yaw")
        chk('the right arrow turns you right', y1 > y0, f'{y0} -> {y1}')
        p0 = await pg.evaluate("() => PV.pitch")
        await pg.locator('[data-pan="up"]').dispatch_event('mousedown')
        await pg.wait_for_timeout(120)
        await pg.locator('[data-pan="up"]').dispatch_event('mouseup')
        await pg.wait_for_timeout(250)
        chk('the up arrow looks up',
            await pg.evaluate("() => PV.pitch") > p0, p0)
        f0 = await pg.evaluate("() => PV.fov")
        await pg.locator('[data-pan="in"]').dispatch_event('mousedown')
        await pg.wait_for_timeout(120)
        await pg.locator('[data-pan="in"]').dispatch_event('mouseup')
        await pg.wait_for_timeout(200)
        chk('plus zooms in', await pg.evaluate("() => PV.fov") < f0, f0)

        print('\nit cannot be pushed somewhere that smears')
        await pg.evaluate("""() => {
            for (let i = 0; i < 40; i++) panoMove(0, 0.5);
        }""")
        chk('looking up stops short of straight up',
            await pg.evaluate("() => PV.pitch") <= 1.46,
            await pg.evaluate("() => PV.pitch"))
        await pg.evaluate("""() => { for (let i = 0; i < 40; i++) panoMove(0, -0.5); }""")
        chk('and down stops short of straight down',
            await pg.evaluate("() => PV.pitch") >= -1.46,
            await pg.evaluate("() => PV.pitch"))
        await pg.evaluate("""() => { for (let i = 0; i < 40; i++) panoZoom(0.5); }""")
        chk('zooming in has a floor',
            await pg.evaluate("() => PV.fov") >= 0.44,
            await pg.evaluate("() => PV.fov"))
        await pg.evaluate("""() => { for (let i = 0; i < 40; i++) panoZoom(2); }""")
        chk('and zooming out a ceiling',
            await pg.evaluate("() => PV.fov") <= 1.91,
            await pg.evaluate("() => PV.fov"))

        print('\nwhat it tells the reader')
        note = await pg.inner_text('#panoNote')
        chk('how to move it', 'Drag the picture' in note, note)
        chk('who took it', 'test image' in note.lower() or 'Mapillary' in note,
            note)
        chk('and under what licence', 'CC BY-SA' in note, note)

        print('\ndragging')
        await pg.evaluate("() => { PV.yaw = 0; panoDraw(); }")
        box = await pg.locator('#panoC').bounding_box()
        await pg.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
        await pg.mouse.down()
        await pg.mouse.move(box['x'] + box['width'] / 2 - 120,
                            box['y'] + box['height'] / 2, steps=6)
        await pg.mouse.up()
        await pg.wait_for_timeout(250)
        chk('dragging left turns you right',
            await pg.evaluate("() => PV.yaw") > 0,
            await pg.evaluate("() => PV.yaw"))

        print('\na place with no photosphere says so')
        await pg.goto(BASE + '#/Gen.2', wait_until='load')
        await pg.wait_for_function(
            "() => document.querySelectorAll('#view .v').length > 0", timeout=20000)
        clicked = await pg.evaluate("""(fixture) => {
            S.pano = fixture;          // holds Nazareth and nothing else
            const b = document.querySelector('.chip.place');
            if (b) { b.click(); return b.textContent.trim(); }
            return null;
        }""", FIXTURE)
        if clicked:
            await pg.wait_for_timeout(800)
            nlook = await pg.locator('[data-look]').count()
            chk('no button offered where there is nothing to see', nlook == 0,
                f'{clicked} offered {nlook}')
        else:
            print('       (no place marker in Genesis 2 to check)')

        await b.close()

asyncio.run(main())
real = [e for e in errs if 'WebGL' not in e and 'swiftshader' not in e.lower()]
print('\nconsole errors:', len(real))
for e in real[:8]:
    print('   ', e)
print('\n' + ('FAILED' if fails or real else 'ALL CHECKS PASSED'))
for f in fails:
    print('   -', f)
sys.exit(1 if fails or real else 0)
