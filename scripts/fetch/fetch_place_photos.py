"""Fetch a photograph of each biblical site from Wikidata + Wikimedia Commons.

The place data already carries a Wikidata id for 655 of the 1,342 places.
Wikidata's P18 points at a photograph on Commons; Commons gives a scaled
copy plus the licence and the photographer, both of which have to travel
with the picture.

Batched 50 at a time through both APIs, so this is ~30 calls rather than
1,300, and polite about it either way.
"""
import json, os, time, urllib.parse, urllib.request

SITE = "https://jebjarrell1974-debug.github.io/jarrell-codex/"
OUT = r"C:\Android\work\placepix"
WIDTH = 640
UA = {"User-Agent": "JarrellCodex/0.1 (https://github.com/jebjarrell1974-debug/jarrell-codex)"}

os.makedirs(OUT, exist_ok=True)
os.makedirs(os.path.join(OUT, "img"), exist_ok=True)

def get(url, raw=False):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read() if raw else json.load(r)
        except Exception as e:
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))

print("reading the published place list...")
places = get(SITE + "data/place.json")
withqid = {n: p for n, p in places.items() if p.get("wd")}
print(f"  {len(places)} places, {len(withqid)} with a Wikidata id")

# ---- 1. Wikidata: which Commons file is the picture of this place? --------
qids = sorted({p["wd"] for p in withqid.values()})
file_of = {}
print(f"asking Wikidata about {len(qids)} entities...")
for i in range(0, len(qids), 50):
    batch = qids[i:i + 50]
    url = ("https://www.wikidata.org/w/api.php?action=wbgetentities&format=json"
           "&props=claims&ids=" + "|".join(batch))
    d = get(url)
    for q, ent in (d.get("entities") or {}).items():
        claims = ent.get("claims", {})
        for prop in ("P18", "P3451", "P5775"):     # image, night view, interior
            if prop in claims:
                try:
                    file_of[q] = claims[prop][0]["mainsnak"]["datavalue"]["value"]
                    break
                except Exception:
                    pass
    print(f"  {min(i+50, len(qids))}/{len(qids)}  found {len(file_of)}", flush=True)
    time.sleep(0.3)

# ---- 2. Commons: a scaled copy, the licence, the photographer -------------
files = sorted(set(file_of.values()))
meta = {}
print(f"asking Commons about {len(files)} files...")
for i in range(0, len(files), 40):
    batch = files[i:i + 40]
    titles = "|".join("File:" + f.replace(" ", "_") for f in batch)
    url = ("https://commons.wikimedia.org/w/api.php?action=query&format=json"
           "&prop=imageinfo&iiprop=url|extmetadata&iiurlwidth=" + str(WIDTH)
           + "&titles=" + urllib.parse.quote(titles))
    try:
        d = get(url)
    except Exception as e:
        print("  batch failed:", e); continue
    norm = {}
    for n in (d.get("query", {}).get("normalized") or []):
        norm[n["to"]] = n["from"]
    for page in (d.get("query", {}).get("pages") or {}).values():
        title = page.get("title", "")
        ii = (page.get("imageinfo") or [{}])[0]
        if not ii.get("thumburl"):
            continue
        em = ii.get("extmetadata", {})
        def m(k):
            v = em.get(k, {}).get("value")
            return v if isinstance(v, str) else None
        key = title[len("File:"):] if title.startswith("File:") else title
        meta[key.replace("_", " ")] = {
            "thumb": ii["thumburl"],
            "w": ii.get("thumbwidth"), "h": ii.get("thumbheight"),
            "page": ii.get("descriptionurl"),
            "licence": m("LicenseShortName"),
            "licurl": m("LicenseUrl"),
            "artist": m("Artist"),
        }
    print(f"  {min(i+40, len(files))}/{len(files)}  resolved {len(meta)}", flush=True)
    time.sleep(0.3)

# ---- 3. download the pictures --------------------------------------------
import re
def strip_html(s):
    if not s:
        return None
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", s).strip()[:120] or None

manifest, got, missing = {}, 0, 0
print("downloading...")
for name, p in sorted(withqid.items()):
    f = file_of.get(p["wd"])
    if not f:
        missing += 1; continue
    info = meta.get(f.replace("_", " ")) or meta.get(f)
    if not info:
        missing += 1; continue
    ext = os.path.splitext(info["thumb"])[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        ext = ".jpg"
    slug = p.get("slug") or re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    dest = os.path.join(OUT, "img", slug + ext)
    if not os.path.exists(dest) or os.path.getsize(dest) == 0:
        try:
            data = get(info["thumb"], raw=True)
            with open(dest, "wb") as fh:
                fh.write(data)
            time.sleep(0.12)
        except Exception as e:
            print(f"  {name}: {e}"); missing += 1; continue
    manifest[name] = {
        "file": slug + ext,
        "w": info["w"], "h": info["h"],
        "licence": info["licence"],
        "licurl": info["licurl"],
        "artist": strip_html(info["artist"]),
        "page": info["page"],
        "status": p.get("status"),
    }
    got += 1
    if got % 50 == 0:
        print(f"  {got} downloaded", flush=True)

with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as fh:
    json.dump(manifest, fh, ensure_ascii=False, indent=1)

total = sum(os.path.getsize(os.path.join(OUT, "img", m["file"]))
            for m in manifest.values()
            if os.path.exists(os.path.join(OUT, "img", m["file"])))
print()
print(f"photographs: {got}")
print(f"no picture on Wikidata: {missing}")
print(f"total size: {total/1048576:.1f} MB")
from collections import Counter
print("licences:", Counter(m["licence"] for m in manifest.values()).most_common(8))
