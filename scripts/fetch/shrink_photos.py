"""Make the place photographs phone-sized.

640px JPEGs averaging 258 KB is a desktop habit. On a phone the picture is
shown about 360 CSS px wide, and the reader may be on a mission field with
no signal and a 10 GB phone. WebP at 720px wide and quality 72 keeps it
sharp on a 2x screen at a third of the weight; JPEG is written alongside
for anything that cannot read WebP.
"""
import os, sys

try:
    from PIL import Image
except ImportError:
    print("Pillow missing. pip install pillow")
    sys.exit(1)

SRC = r"C:\Android\work\placepix\img"
DST = r"C:\Android\work\placepix\web"
MAXW = 720
os.makedirs(DST, exist_ok=True)

before = after = n = skipped = 0
for fn in sorted(os.listdir(SRC)):
    p = os.path.join(SRC, fn)
    if not os.path.isfile(p):
        continue
    before += os.path.getsize(p)
    stem = os.path.splitext(fn)[0]
    out = os.path.join(DST, stem + ".webp")
    try:
        im = Image.open(p)
        im.load()
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        if im.width > MAXW:
            h = round(im.height * MAXW / im.width)
            im = im.resize((MAXW, h), Image.LANCZOS)
        im.save(out, "WEBP", quality=72, method=6)
        after += os.path.getsize(out)
        n += 1
    except Exception as e:
        print(f"  {fn}: {e}")
        skipped += 1

print(f"converted {n} ({skipped} failed)")
print(f"  before {before/1048576:.1f} MB")
print(f"  after  {after/1048576:.1f} MB   ({100*after/before:.0f}%)")
if n:
    print(f"  average now {after/n/1024:.0f} KB")
