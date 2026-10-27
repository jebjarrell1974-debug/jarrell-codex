"""Fetch Gustave Dore's Bible engravings from Commons.

Dore died in 1883, so the engravings are unambiguously public domain - no
fair-use argument, no "19th-century and later" ambiguity. Exactly the kind
of thing that can go into something meant to be copied and handed out.

Commons keeps the scripture reference in the file DESCRIPTION rather than
the title ("The Creation of Light (Gen. 1:1-5)"), so the description is
carried back whole and parsed where the book-name table lives.
"""
import json, os, re, time, urllib.parse, urllib.request

UA = {"User-Agent": "JarrellCodex/0.1 (open-source Bible study)"}
API = "https://commons.wikimedia.org/w/api.php"
CAT = "Category:Doré's English Bible"
OUT = r"C:\Android\work\dore"
WIDTH = 900

os.makedirs(os.path.join(OUT, "img"), exist_ok=True)

def get(url, raw=False):
    for a in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read() if raw else json.load(r)
        except Exception:
            if a == 3:
                raise
            time.sleep(2 * (a + 1))

def plain(v):
    if not isinstance(v, str):
        return None
    v = re.sub(r"<[^>]+>", " ", v)
    v = v.replace("&amp;", "&").replace("&nbsp;", " ").replace("&quot;", '"')
    return re.sub(r"\s+", " ", v).strip() or None

members, cont = [], None
while True:
    u = (API + "?action=query&format=json&list=categorymembers&cmtype=file&cmlimit=500"
         "&cmtitle=" + urllib.parse.quote(CAT))
    if cont:
        u += "&cmcontinue=" + urllib.parse.quote(cont)
    d = get(u)
    members += [m["title"] for m in d["query"]["categorymembers"]]
    cont = d.get("continue", {}).get("cmcontinue")
    if not cont:
        break

numbered = [t for t in members if re.match(r"File:\d{3}\.", t)]
print(f"{len(members)} files in the category, {len(numbered)} numbered plates")

records = {}
for i in range(0, len(numbered), 40):
    batch = numbered[i:i + 40]
    u = (API + "?action=query&format=json&prop=imageinfo&iiprop=url|extmetadata"
         "&iiurlwidth=" + str(WIDTH) + "&titles=" + urllib.parse.quote("|".join(batch)))
    d = get(u)
    for page in d["query"]["pages"].values():
        title = page.get("title", "")
        ii = (page.get("imageinfo") or [{}])[0]
        if not ii.get("thumburl"):
            continue
        em = ii.get("extmetadata", {})
        m = re.match(r"File:(\d{3})\.(.+)\.(jpg|jpeg|png)$", title, re.I)
        records[title] = {
            "plate": int(m.group(1)) if m else None,
            "title": (m.group(2).replace("_", " ") if m else title[5:]),
            "desc": plain(em.get("ImageDescription", {}).get("value")),
            "licence": plain(em.get("LicenseShortName", {}).get("value")),
            "artist": plain(em.get("Artist", {}).get("value")),
            "page": ii.get("descriptionurl"),
            "thumb": ii["thumburl"],
            "w": ii.get("thumbwidth"), "h": ii.get("thumbheight"),
        }
    print(f"  metadata {min(i+40, len(numbered))}/{len(numbered)}", flush=True)
    time.sleep(0.3)

withdesc = sum(1 for r in records.values() if r["desc"])
print(f"\n{len(records)} plates resolved, {withdesc} carry a description")

got = 0
for title, r in sorted(records.items(), key=lambda kv: kv[1]["plate"] or 999):
    ext = os.path.splitext(r["thumb"])[1].lower() or ".jpg"
    if ext not in (".jpg", ".jpeg", ".png"):
        ext = ".jpg"
    fn = f"{r['plate']:03d}{ext}" if r["plate"] else re.sub(r"\W+", "-", r["title"])[:40] + ext
    dest = os.path.join(OUT, "img", fn)
    if not os.path.exists(dest) or os.path.getsize(dest) == 0:
        try:
            with open(dest, "wb") as fh:
                fh.write(get(r["thumb"], raw=True))
            time.sleep(0.12)
        except Exception as e:
            print(f"  {title}: {e}")
            continue
    r["file"] = fn
    got += 1
    if got % 40 == 0:
        print(f"  downloaded {got}", flush=True)

with open(os.path.join(OUT, "plates.json"), "w", encoding="utf-8") as fh:
    json.dump({k: v for k, v in records.items() if v.get("file")}, fh,
              ensure_ascii=False, indent=1)

total = sum(os.path.getsize(os.path.join(OUT, "img", r["file"]))
            for r in records.values() if r.get("file"))
print(f"\nengravings: {got}")
print(f"total: {total/1048576:.1f} MB")
from collections import Counter
print("licences:", Counter(r["licence"] for r in records.values()).most_common())
