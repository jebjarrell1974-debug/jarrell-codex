import os
from PIL import Image
SRC = r"C:\Android\work\dore\img"; DST = r"C:\Android\work\dore\web"
MAXW = 820
before = after = n = 0
for fn in sorted(os.listdir(SRC)):
    p = os.path.join(SRC, fn)
    if not os.path.isfile(p): continue
    before += os.path.getsize(p)
    out = os.path.join(DST, os.path.splitext(fn)[0] + ".webp")
    try:
        im = Image.open(p); im.load()
        if im.mode not in ("RGB","L"): im = im.convert("RGB")
        if im.width > MAXW:
            im = im.resize((MAXW, round(im.height*MAXW/im.width)), Image.LANCZOS)
        # engravings are grey line art; dropping the colour channels costs
        # nothing visually and a good deal of weight
        if im.mode != "L":
            ext = im.convert("RGB").getextrema()
            flat = all(abs(c[1]-c[0]) < 255 for c in ext) and \
                   max(abs(ext[0][i]-ext[1][i]) for i in (0,1)) < 40
            if flat: im = im.convert("L")
        im.save(out, "WEBP", quality=68, method=6)
        after += os.path.getsize(out); n += 1
    except Exception as e: print(f"  {fn}: {e}")
print(f"converted {n}")
print(f"  {before/1048576:.1f} MB -> {after/1048576:.1f} MB ({100*after/before:.0f}%)  avg {after/n/1024:.0f} KB")
