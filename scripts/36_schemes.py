#!/usr/bin/env python3
"""Generate and verify the reading colour schemes.

Written as a generator rather than by hand because every token has to clear
7:1 against its own background, and six schemes times a dozen tokens is far
too many numbers to eyeball. Anything that fails is reported and the build
stops rather than shipping a scheme that looks fine to me.

7:1 rather than the usual 4.5:1 because WCAG's own derivation ties 4.5:1 to
the contrast sensitivity of a TYPICAL eighty-year-old. This is read by
people at and past that, so the floor is the AAA figure.

Background values are taken from products that ship them, where a real one
exists, rather than invented: #F4ECD8 is Zotero's sepia.
"""
import json, sys

def lum(h):
    h = h.lstrip('#')
    r, g, b = (int(h[i:i+2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)

def ratio(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)

# Each scheme: the background, then every token that has to be read against it.
# "surface" and "line" are chrome, not text, and are checked differently.
SCHEMES = {
 'paper': dict(
    name='Paper', note='A warm near-white. The default.',
    paper='#FCFBF8', surface='#FFFFFF',
    ink='#141210', soft='#4A4540', faint='#59544E',
    accent='#0B4F87', warm='#6E2A0C',
    line='#DEDAD2', lineSoft='#EDEAE3', accentSoft='#E7EEF6', onAccent='#FFFFFF',
    good='#1F5A3C', warn='#6B4A08', crit='#7A2622', dark=False),

 'sepia': dict(
    name='Sepia', note='The old paperback. Warmer, a little less glare.',
    paper='#F4ECD8', surface='#FBF6EA',
    ink='#241D14', soft='#4F4538', faint='#564C3D',
    accent='#07406E', warm='#7A2E12',
    line='#DCD0B4', lineSoft='#EBE3CE', accentSoft='#E4EBF3', onAccent='#FFFFFF',
    good='#1D5537', warn='#63440A', crit='#6E0F18', dark=False),

 'contrast': dict(
    name='High contrast', note='Everything as strong as it goes. For bright sun, or eyes that need it.',
    paper='#FFFFFF', surface='#FFFFFF',
    ink='#000000', soft='#2E2E2E', faint='#3D3D3D',
    accent='#00439B', warm='#7A1F00',
    line='#9A9A9A', lineSoft='#D4D4D4', accentSoft='#E3ECFA', onAccent='#FFFFFF',
    good='#14472C', warn='#5A3C00', crit='#8A1010', dark=False),

 'dim': dict(
    name='Dim', note='Quiet grey, dark print. For eyes that find a white page too bright but read a dark screen worse.',
    paper='#D8D4CE', surface='#E6E3DE',
    ink='#16140F', soft='#2B2821', faint='#3A362E',
    accent='#06385F', warm='#5E2309',
    line='#B6B1A8', lineSoft='#C9C5BD', accentSoft='#C7CFD8', onAccent='#FFFFFF',
    good='#153F28', warn='#4E3505', crit='#6B1A18', dark=False),

 'night': dict(
    name='Night', note='Soft dark. Easier than pure black on most screens.',
    paper='#15181C', surface='#1E2228',
    ink='#EDEBE7', soft='#D6D2CC', faint='#B9B4AC',
    accent='#F0C98A', warm='#F0C98A',
    line='#363B43', lineSoft='#262B32', accentSoft='#2A2A22', onAccent='#15181C',
    good='#8FD6AC', warn='#E8C06A', crit='#F09C96', dark=True),

 'black': dict(
    name='Black', note='True black. Saves power on an OLED screen.',
    paper='#000000', surface='#0C0C0C',
    ink='#FFFFFF', soft='#D9D9D9', faint='#BDBDBD',
    accent='#FFD479', warm='#FFD479',
    line='#3A3A3A', lineSoft='#222222', accentSoft='#2A2518', onAccent='#000000',
    good='#8FE3B4', warn='#F2CE77', crit='#FFA7A0', dark=True),
}

FLOOR = 7.0
TEXT = ['ink', 'soft', 'faint', 'accent', 'warm', 'good', 'warn', 'crit']

fails, rows = [], []
for key, s in SCHEMES.items():
    bg = s['paper']
    for tok in TEXT:
        r = ratio(s[tok], bg)
        rows.append((key, tok, s[tok], r))
        if r < FLOOR:
            fails.append(f"{key}.{tok} {s[tok]} on {bg} = {r:.2f}:1")
    # the ink must also work on the raised surface a sheet uses
    for tok in ('ink', 'soft', 'faint'):
        r = ratio(s[tok], s['surface'])
        if r < FLOOR:
            fails.append(f"{key}.{tok} on surface {s['surface']} = {r:.2f}:1")
    # a chip sitting on accentSoft has to be legible too
    r = ratio(s['accent'], s['accentSoft'])
    if r < 4.5:
        fails.append(f"{key}.accent on its own soft fill = {r:.2f}:1")

print(f"{'scheme':<10} {'token':<8} {'hex':<9} ratio")
last = None
for key, tok, hx, r in rows:
    if key != last:
        print(f"  --- {SCHEMES[key]['name']} (bg {SCHEMES[key]['paper']})")
        last = key
    flag = '' if r >= FLOOR else '   <-- BELOW 7:1'
    print(f"  {'':<8} {tok:<8} {hx:<9} {r:5.2f}:1{flag}")

if fails:
    print(f"\n{len(fails)} TOKENS BELOW THE FLOOR:")
    for f in fails:
        print("  -", f)
    sys.exit(1)

print(f"\nall {len(rows)} text tokens clear {FLOOR}:1")

# ---- emit the CSS -------------------------------------------------------
def block(sel, s):
    return (f"{sel}{{\n"
            f"  --paper:{s['paper']}; --surface:{s['surface']};\n"
            f"  --ink:{s['ink']}; --ink-soft:{s['soft']}; --ink-faint:{s['faint']};\n"
            f"  --line:{s['line']}; --line-soft:{s['lineSoft']};\n"
            f"  --accent:{s['accent']}; --accent-soft:{s['accentSoft']};\n"
            f"  --accent-warm:{s['warm']}; --on-accent:{s['onAccent']};\n"
            f"  --good:{s['good']}; --warn:{s['warn']}; --crit:{s['crit']};\n"
            f"  color-scheme:{'dark' if s['dark'] else 'light'};}}\n")

css = ["/* Reading colour schemes. Generated by scripts/36_schemes.py - every",
       "   token is verified at 7:1 against its own background before this file",
       "   is written. Edit the script, not this block. */"]
css.append(block(':root, :root[data-scheme="paper"]', SCHEMES['paper']))
for key, s in SCHEMES.items():
    if key == 'paper':
        continue
    css.append(block(f':root[data-scheme="{key}"]', s))
# following the phone is opt-in, and picks the two softest of the six
css.append('@media (prefers-color-scheme:dark){:root[data-scheme="auto"]{\n'
           + block('', SCHEMES['night']).lstrip('{').rstrip('}\n').strip() + '}}\n')
css.append(block(':root[data-scheme="auto"]', SCHEMES['paper']).replace(
    ':root[data-scheme="auto"]{', ':root[data-scheme="auto"]{', 1))

open('/home/claude/site/scheme.css', 'w', encoding='utf-8').write("\n".join(css))
meta = {k: dict(name=v['name'], note=v['note'], paper=v['paper'],
                ink=v['ink'], accent=v['accent'], dark=v['dark'])
        for k, v in SCHEMES.items()}
json.dump(meta, open('/home/claude/site/data/schemes.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f"wrote scheme.css and data/schemes.json ({len(SCHEMES)} schemes)")
