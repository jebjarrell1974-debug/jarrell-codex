"""Check the notes / cross-reference / About queries the app now runs."""
import os, sqlite3, sys

DB = r"C:\Android\work\verify\codex.db"
fails = []
def chk(name, cond, detail=""):
    print(("  ok   " if cond else "  FAIL ") + name + (("  " + str(detail)[:280]) if not cond else ""))
    if not cond:
        fails.append(name)

db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)

print("notes")
n = db.execute(
    "SELECT quote, category, body, source FROM note WHERE verse_key = ? ORDER BY note_id",
    ("Jhn.3.16",)).fetchall()
chk("notes(Jhn.3.16) returns rows", len(n) > 0, len(n))
chk("bodies are not empty", all(r[2].strip() for r in n))
chk("a source is attached to every note", all(r[3].strip() for r in n))
chk("source names unfoldingWord and its licence",
    n and "unfoldingWord" in n[0][3] and "CC BY" in n[0][3], n[0][3] if n else None)

counts = {}
for v, k in db.execute(
        "SELECT verse, COUNT(*) FROM note WHERE book = ? AND chapter = ? GROUP BY verse",
        ("Jhn", 3)):
    counts[v] = k
chk("noteCounts(Jhn,3) agrees with notes() for v16",
    counts.get(16) == len(n), f"{counts.get(16)} vs {len(n)}")
chk("most of John 3 has notes", len(counts) >= 30, len(counts))

print("\ncross-references")
x = db.execute(
    "SELECT to_key, to_end_key, votes FROM xref WHERE from_key = ? ORDER BY votes DESC LIMIT ?",
    ("Jhn.3.16", 60)).fetchall()
chk("xrefs(Jhn.3.16) returns rows", len(x) > 0, len(x))
chk("sorted heaviest first",
    all(x[i][2] >= x[i + 1][2] for i in range(len(x) - 1)), [r[2] for r in x[:5]])
chk("top link is Romans 5:8", x and x[0][0] == "Rom.5.8", x[0] if x else None)
chk("every target is a real verse",
    all(db.execute("SELECT 1 FROM verse WHERE verse_key = ?", (r[0],)).fetchone()
        for r in x[:25]),
    [r[0] for r in x[:3]])

# the label the UI builds
def label(to_key, to_end, name):
    p = to_key.split(".")
    if len(p) < 3:
        return name
    base = f"{name} {p[1]}:{p[2]}"
    if not to_end:
        return base
    e = to_end.split(".")
    if len(e) < 3:
        return base
    return f"{base}-{e[2]}" if e[1] == p[1] else f"{base} \u2013 {e[1]}:{e[2]}"

chk("a single-verse label reads 'Romans 5:8'",
    label("Rom.5.8", None, "Romans") == "Romans 5:8",
    label("Rom.5.8", None, "Romans"))
chk("a same-chapter range collapses",
    label("Rom.5.8", "Rom.5.10", "Romans") == "Romans 5:8-10",
    label("Rom.5.8", "Rom.5.10", "Romans"))
chk("a cross-chapter range does not pretend otherwise",
    label("Rom.5.8", "Rom.6.2", "Romans") == "Romans 5:8 \u2013 6:2",
    label("Rom.5.8", "Rom.6.2", "Romans"))

ranges = db.execute("SELECT COUNT(*) FROM xref WHERE to_end_key IS NOT NULL").fetchone()[0]
print(f"       ({ranges:,} of the cross-references are ranges)")

print("\nAbout screen")
t = db.execute("SELECT code, name, licence FROM translation ORDER BY code").fetchall()
chk("four translations with a licence each",
    len(t) == 4 and all(r[2].strip() for r in t), t)
chk("all four are public domain", all("ublic domain" in r[2] for r in t), [r[2] for r in t])
s = db.execute(
    "SELECT scheme_id, name, coverage, summary, source, is_default FROM chronology_scheme ORDER BY sort_order"
).fetchall()
chk("six schemes, each with a summary", len(s) == 6 and all(r[3].strip() for r in s), len(s))
cn = db.execute("SELECT heading, body FROM chronology_note ORDER BY sort_order").fetchall()
chk("chronology notes present for About", len(cn) >= 4 and all(r[1].strip() for r in cn), len(cn))

print()
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURES: {fails}")
sys.exit(1 if fails else 0)
