"""Build a chapter -> recording index from public-domain LibriVox readings.

Two sources, in order of preference:

  1. A per-book item whose files are one chapter each. Exact, so the reader
     presses play and hears that chapter from its first word.
  2. The complete 2001 reading, whose 127 files carry a book and a chapter
     range in their titles ("001 - Genesis Ch. 1 - 14"). Covers everything,
     but a chapter starts partway into the file - which the reader is told,
     rather than being left to wonder why it began in the wrong place.

Nothing is hosted. These stream from archive.org, which is where they live
and who pays for them.

A mapping is only written when the chapter range parsed from a title lies
inside the book's real chapter count, read from the published books.json.
"""
import json, re, time, urllib.parse, urllib.request
from collections import defaultdict

UA = {"User-Agent": "JarrellCodex/0.1 (open-source Bible study)"}
SITE = "https://jebjarrell1974-debug.github.io/jarrell-codex/"
COMPLETE = "bible_kjv_complete_2001_librivox"
OUT = r"C:\Android\work\audio.json"

def get(u, tries=3):
    for a in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=90) as r:
                return json.load(r)
        except Exception:
            if a == tries - 1:
                raise
            time.sleep(2 * (a + 1))

books = get(SITE + "data/books.json")
CHAPTERS = {b[0]: b[3] for b in books["books"]}
NAMES = books["names"]

LOOKUP = {}
for code, names in NAMES.items():
    for n in names:
        LOOKUP[n.lower().replace('.', '').strip()] = code
LOOKUP.update({'psalm': 'Psa', 'psalms': 'Psa', 'song of solomon': 'Sng',
               'canticles': 'Sng', 'revelation of john': 'Rev'})

index = defaultdict(dict)          # book -> chapter -> record
sources = {}

# ---- 1. the complete reading: book + range in every title ----------------
m = get(f"https://archive.org/metadata/{COMPLETE}")
lic = (m["metadata"].get("licenseurl") or "")
assert "publicdomain" in lic, f"complete set is not public domain: {lic}"
sources[COMPLETE] = {"title": m["metadata"].get("title"), "licence": lic,
                     "page": f"https://archive.org/details/{COMPLETE}"}
base = f"https://archive.org/download/{COMPLETE}/"

# "001 - Genesis Ch. 1 - 14" and also "052 - Psalms 1 - 32": the Psalms
# files carry no "Ch." because psalms are numbered, not chaptered, and
# requiring it silently dropped all 150 of them.
TITLE_RE = re.compile(r"^\s*\d+\s*-\s*(.+?)\s+(?:Ch\.?\s*)?(\d+)\s*(?:-\s*(\d+))?\s*$", re.I)
placed = skipped = 0
for f in m.get("files", []):
    n = f.get("name", "")
    if not n.endswith("_64kb.mp3"):
        continue
    t = f.get("title") or ""
    g = TITLE_RE.match(t)
    if not g:
        skipped += 1
        continue
    bk = LOOKUP.get(g.group(1).lower().replace('.', '').strip())
    if not bk:
        skipped += 1
        continue
    a, b = int(g.group(2)), int(g.group(3) or g.group(2))
    if a < 1 or b > CHAPTERS.get(bk, 0) or a > b:
        skipped += 1
        continue
    for ch in range(a, b + 1):
        index[bk][ch] = {
            "url": base + n, "exact": False,
            "covers": f"{g.group(1).strip()} {a}" + (f"\u2013{b}" if b != a else ""),
            "item": COMPLETE,
            "mb": round(int(f.get("size", 0)) / 1048576, 1),
        }
        placed += 1
print(f"complete reading: {placed} chapters mapped, {skipped} files unparsed")

# ---- 2. per-chapter items, which beat a range ----------------------------
EXACT_RE = re.compile(r"\bchapter\s+(\d{1,3})\s*$", re.I)
seen = {}
for q in ('collection:librivoxaudio AND title:"King James"',
          'collection:librivoxaudio AND identifier:*_kjv_*'):
    u = ("https://archive.org/advancedsearch.php?q=" + urllib.parse.quote(q) +
         "&fl%5B%5D=identifier&fl%5B%5D=title&rows=400&page=1&output=json")
    try:
        for x in get(u)["response"]["docs"]:
            seen[x["identifier"]] = x.get("title") or ""
    except Exception as e:
        print("  search failed:", e)

def book_of(title):
    t = re.sub(r"\(.*?\)", " ", title).lower()
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    best = None
    for code, names in NAMES.items():
        for nm in names:
            n = nm.lower()
            if len(n) < 3:
                continue
            if re.search(r"\b" + re.escape(n) + r"\b", t) and (best is None or len(n) > best[1]):
                best = (code, len(n))
    return best[0] if best else None

exact_books = 0
for ident, title in sorted(seen.items()):
    if ident == COMPLETE:
        continue
    bk = book_of(title)
    if not bk:
        continue
    try:
        mm = get(f"https://archive.org/metadata/{ident}")
    except Exception:
        continue
    l2 = (mm.get("metadata", {}).get("licenseurl") or "").lower()
    if "publicdomain" not in l2:
        continue
    got = {}
    for f in mm.get("files", []):
        n = f.get("name", "")
        if not n.endswith("_64kb.mp3"):
            continue
        g = EXACT_RE.search(f.get("title") or "")
        if not g:
            continue
        c = int(g.group(1))
        if c in got:
            got = {}
            break
        got[c] = (n, int(f.get("size", 0)))
    if got and set(got) == set(range(1, CHAPTERS[bk] + 1)):
        b2 = f"https://archive.org/download/{ident}/"
        for c, (n, sz) in got.items():
            index[bk][c] = {"url": b2 + n, "exact": True, "covers": None,
                            "item": ident, "mb": round(sz / 1048576, 1)}
        sources[ident] = {"title": title,
                          "licence": mm["metadata"].get("licenseurl"),
                          "page": f"https://archive.org/details/{ident}"}
        exact_books += 1
        print(f"  exact: {bk:<4} {CHAPTERS[bk]:>3} ch  {ident[:42]}")
    time.sleep(0.12)

total = sum(len(v) for v in index.values())
exact = sum(1 for v in index.values() for r in v.values() if r["exact"])
print(f"\nbooks with audio   : {len(index)} of {len(CHAPTERS)}")
print(f"chapters with audio: {total} of {sum(CHAPTERS.values())}")
print(f"  exact (one chapter per file): {exact}")
print(f"  inside a longer recording   : {total - exact}")
gaps = sorted(set(CHAPTERS) - set(index))
print("no audio at all for:", " ".join(gaps) or "nothing")

json.dump({"chapters": {f"{b}.{c}": r for b, v in index.items() for c, r in v.items()},
           "sources": sources},
          open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
import os
print(f"\nwrote {OUT} ({os.path.getsize(OUT)/1024:.0f} KB)")

