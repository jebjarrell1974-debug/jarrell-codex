"""Re-check the live site after the night's changes, as a phone would."""
import json, sys, urllib.request

BASE = "https://jebjarrell1974-debug.github.io/jarrell-codex/"
UA = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile Safari/605.1.15"}
fails = []

def chk(name, cond, detail=""):
    print(("  ok   " if cond else "  FAIL ") + name + (("  " + str(detail)[:180]) if not cond else ""))
    if not cond:
        fails.append(name)

def fetch(path, binary=False):
    with urllib.request.urlopen(urllib.request.Request(BASE + path, headers=UA), timeout=60) as r:
        return r.status, (r.read() if binary else r.read().decode("utf-8", "replace"))

print("the shell")
st, html = fetch("")
chk("page served", st == 200, st)
for want in ('id="btnAa"', 'scheme.css', 'app.css', 'app.js', 'theme-color'):
    chk(f"references {want}", want in html)

print("\nthe code")
st, js = fetch("app.js")
chk("app.js served", st == 200, st)
for want, why in [("data-setscheme3", "the colour swatches"),
                  ("data-setpix", "the engraving switch"),
                  ("dore.json", "the engravings"),
                  ("pix_manifest.json", "the photographs"),
                  ("data-fs", "text size"),
                  ("SCHEME_ORDER", "the scheme list")]:
    chk(f"carries {why}", want in js, want)

st, css = fetch("scheme.css")
chk("scheme.css served", st == 200, st)
for k in ("paper", "sepia", "contrast", "dim", "night", "black"):
    chk(f"scheme '{k}' defined", f'data-scheme="{k}"' in css or k == "paper")

print("\nthe data")
for path, key in [("data/books.json", "books"), ("data/schemes.json", "paper"),
                  ("data/dore.json", "plates"), ("data/pix_manifest.json", None),
                  ("data/offline_manifest.json", "tiers"),
                  ("data/ch/Gen.1.json", "v")]:
    try:
        st, body = fetch(path)
        d = json.loads(body)
        chk(path, st == 200 and (key is None or key in d), st)
    except Exception as e:
        chk(path, False, e)

print("\nthe pictures actually download")
st, man = fetch("data/pix_manifest.json")
pm = json.loads(man)
f = pm[list(pm)[0]]["file"]
st, raw = fetch("data/pix/" + f, binary=True)
chk(f"a photograph ({f})", st == 200 and raw[:4] == b"RIFF", f"{st} {len(raw)}b")

st, dj = fetch("data/dore.json")
dd = json.loads(dj)
pl = dd["plates"][list(dd["plates"])[0]]
st, raw = fetch("data/dore/" + pl["file"], binary=True)
chk(f"an engraving ({pl['file']})", st == 200 and raw[:4] == b"RIFF", f"{st} {len(raw)}b")
chk("every engraving is public domain",
    all("ublic domain" in (p.get("licence") or "") for p in dd["plates"].values()))
chk("Genesis 1:1 has a plate", "Gen.1.1" in dd["at"], list(dd["at"])[:3])

print("\noffline")
st, sw = fetch("sw.js")
chk("sw.js served", st == 200, st)
chk("scheme.css is precached", "scheme.css" in sw)
chk("cache is content-stamped", "const BUILD = '" in sw and "__BUILD__" not in sw)
st, om = fetch("data/offline_manifest.json")
tiers = json.loads(om)["tiers"]
chk("six download tiers", len(tiers) == 6, list(tiers))
total = sum(t["bytes"] for t in tiers.values())
print(f"       everything offline = {total/1048576:.0f} MB in {sum(t['count'] for t in tiers.values()):,} files")

print()
print("THE LIVE SITE IS GOOD" if not fails else f"{len(fails)} PROBLEMS: {fails}")
sys.exit(1 if fails else 0)
