"""Check the navigation query the app now uses, against the real database.

Specifically the thing that was already broken on the website: the display
name. Taking "the longest name" turns 1 Samuel into First Samuel, and Job
has no 'full' row at all, so a naive lookup renders nothing.
"""
import os, sqlite3, sys

DB = r"C:\Android\work\verify\codex.db"
fails = []
def chk(name, cond, detail=""):
    print(("  ok   " if cond else "  FAIL ") + name + (("  " + str(detail)[:300]) if not cond else ""))
    if not cond:
        fails.append(name)

if not os.path.exists(DB):
    print("run verify_apk.py first to unpack the database"); sys.exit(1)

db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)

# the DAO's books() query, verbatim
SQL = """SELECT v.book, v.book_order, v.testament, MAX(v.chapter) AS chapters,
                (SELECT b.name FROM book_name b
                  WHERE b.book = v.book AND b.kind = 'full'
                  ORDER BY b.rowid LIMIT 1) AS full_name
         FROM verse v GROUP BY v.book, v.book_order, v.testament
         ORDER BY v.book_order"""
rows = db.execute(SQL).fetchall()

chk("books() returns 66", len(rows) == 66, len(rows))
chk("ordered Genesis first, Revelation last",
    rows and rows[0][0] == "Gen" and rows[-1][0] == "Rev",
    (rows[0][0], rows[-1][0]) if rows else None)

# the Kotlin does: name = full_name ?: book
named = [(r[0], (r[4] or r[0])) for r in rows]
blank = [n for n in named if not n[1] or not n[1].strip()]
chk("every book has a non-empty display name", not blank, blank)

want = {
    "Gen": "Genesis", "Job": "Job", "1Sa": "1 Samuel", "Sng": "Song of Solomon",
    "Jhn": "John", "Php": "Philippians", "Rev": "Revelation", "3Jn": "3 John",
}
got = dict(named)
for code, expect in want.items():
    chk(f"{code} -> {expect!r}", got.get(code) == expect, got.get(code))

chk("no name is a longest-match artefact",
    got.get("1Sa") != "First Samuel" and got.get("Rev") != "Revelation of John",
    (got.get("1Sa"), got.get("Rev")))

counts = {r[0]: r[3] for r in rows}
for code, n in (("Psa", 150), ("Gen", 50), ("Job", 42), ("Jud", 1), ("Rev", 22)):
    chk(f"{code} has {n} chapters", counts.get(code) == n, counts.get(code))

ot = [r for r in rows if r[2] == "OT"]
nt = [r for r in rows if r[2] == "NT"]
chk("39 OT and 27 NT", len(ot) == 39 and len(nt) == 27, (len(ot), len(nt)))

# the stepper must be able to walk the whole canon without falling off
order = [r[0] for r in rows]
total = sum(counts[c] for c in order)
chk("1,189 chapters in all", total == 1189, total)

steps, book_i, ch = 0, 0, 1
while steps < 2000:
    if ch < counts[order[book_i]]:
        ch += 1
    elif book_i < len(order) - 1:
        book_i += 1; ch = 1
    else:
        break
    steps += 1
chk("stepping forward reaches the last chapter of Revelation",
    order[book_i] == "Rev" and ch == counts["Rev"] and steps == total - 1,
    (order[book_i], ch, steps))

print()
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURES: {fails}")
sys.exit(1 if fails else 0)
