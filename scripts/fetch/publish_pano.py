# -*- coding: utf-8 -*-
"""Publish the photospheres, after checking they are what they claim.

Every one of these is somebody else's photograph under a share-alike
licence. Publishing one without the author named is the one thing this
project must not do, so that is checked here and the push is refused
rather than reported.
"""
import io, json, os, shutil, subprocess, sys
from PIL import Image

GHP = r'C:\Android\work\ghp3'
SRC = r'C:\Android\work\panoout'
MAN = r'C:\Android\work\pano.json'
DEST = os.path.join(GHP, 'data', 'pano')

man = json.load(io.open(MAN, encoding='utf-8'))
print(f'places    : {len(man)}')
files = sorted(set(m['file'] for m in man.values()))
print(f'images    : {len(files)}')

bad = []
for name, m in man.items():
    if not m.get('artist'):
        bad.append((name, 'no author named'))
    lic = str(m.get('licence', '')).lower()
    if not ('by-sa' in lic or 'by 2' in lic or 'by 3' in lic
            or 'by 4' in lic or 'cc0' in lic or 'public domain' in lic):
        bad.append((name, 'licence not one we can pass on: ' + m.get('licence', '')))
    if not m.get('page'):
        bad.append((name, 'no link to where it came from'))
    p = os.path.join(SRC, m['file'])
    if not os.path.exists(p):
        bad.append((name, 'image missing'))
        continue
    with Image.open(p) as im:
        if (im.width, im.height) != (2048, 1024):
            bad.append((name, f'{im.width}x{im.height}, not 2048x1024'))
if bad:
    print(f'\nREFUSING TO PUBLISH - {len(bad)} problems:')
    for n, why in bad[:20]:
        print(f'   {n[:26]:<28} {why}')
    sys.exit(1)
print('every one names its author, its licence and its source, '
      'and is 2048x1024')

os.makedirs(DEST, exist_ok=True)
total = 0
for f in files:
    shutil.copy2(os.path.join(SRC, f), os.path.join(DEST, f))
    total += os.path.getsize(os.path.join(DEST, f))
io.open(os.path.join(GHP, 'data', 'pano.json'), 'w', encoding='utf-8').write(
    json.dumps(man, ensure_ascii=False, separators=(',', ':')))
print(f'copied {len(files)} images, {total / 1048576:.1f} MB')

msg = os.path.join(r'C:\Android\work', 'pano_pub_msg.txt')
io.open(msg, 'w', encoding='utf-8').write(
    """Photospheres: 25 places you can stand in and turn round

Full 360 equirectangular photographs for 25 of the 808 located places,
including Mount Sinai, Nazareth, Bethlehem, Hebron, Jericho, Machpelah,
Mamre, Rome, Athens, the Areopagus and Thessalonica. 20 distinct images,
3.5 MB in total, every one 2048x1024.

They come from Mapillary by way of Wikimedia Commons, which is to say
somebody walked up there with a camera. 24 are CC BY-SA 4.0 and one is
CC BY 2.5, so all of them can be kept offline and passed on, which is the
whole point - and every one names its author and links the page it came
from. Nothing publishes without that; the check refuses rather than warns.

Twenty-five out of eight hundred is the honest number. Mapillary follows
roads and footpaths, so a site has one if somebody has walked it. The
search radius is 3 km, not 8, because at 8 km Jerusalem picks up
photospheres of Bethlehem streets and labels them Jerusalem. Each place
records how far off its photosphere was taken and the viewer says so when
it is more than 200 m.

The originals run to 12288x6144 and twenty-odd megabytes. Commons was
asked for a 2048-wide thumbnail instead of the full file, so the resizing
happened on their side by design rather than ours by accident, and the
quality is walked down until each image fits under 360 KB rather than
picked and hoped for.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01V8b4m9oP8kbZpQam46xKJK
""")

for cmd in (['git', 'add', '-A'],
            ['git', '-c', 'user.name=Jeb Jarrell',
             '-c', 'user.email=jebjarrell1974@gmail.com',
             'commit', '-q', '-F', msg],
            ['git', 'push', '-q', 'origin', 'gh-pages']):
    r = subprocess.run(cmd, cwd=GHP)
    if r.returncode != 0:
        print('FAILED:', ' '.join(cmd))
        sys.exit(1)
print(subprocess.run(['git', 'log', '--oneline', '-1'], cwd=GHP,
                     capture_output=True, text=True).stdout.strip())
