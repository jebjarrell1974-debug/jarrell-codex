"""Check the search queries the app now runs, including the awkward input."""
import re, sqlite3, sys, time

DB = r"C:\Android\work\verify\codex.db"
fails = []
def chk(name, cond, detail=""):
    print(("  ok   " if cond else "  FAIL ") + name + (("  " + str(detail)[:280]) if not cond else ""))
    if not cond:
        fails.append(name)

db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)

def fts(raw):
    parts = [p for p in re.split(r"\s+", raw.strip()) if p]
    return " ".join('"' + p.replace('"', "") + '"' for p in parts) or '""'

V = """SELECT s.verse_key, s.code, s.text
       FROM search_verse s JOIN verse v ON v.verse_key = s.verse_key
       WHERE search_verse MATCH ? AND s.code = 'KJV'
       ORDER BY v.book_order, v.chapter, v.verse LIMIT ?"""
N = """SELECT n.verse_key, substr(n.body,1,180) AS text
       FROM search_note s JOIN note n ON n.note_id = s.note_id
       JOIN verse v ON v.verse_key = n.verse_key
       WHERE search_note MATCH ?
       ORDER BY v.book_order, v.chapter, v.verse LIMIT ?"""
L = """SELECT strongs, lemma, gloss,
              CASE WHEN lower(gloss) LIKE ? THEN 0
                   WHEN lower(lemma) LIKE ? THEN 1 ELSE 2 END AS rank
       FROM search_lexicon WHERE search_lexicon MATCH ?
       ORDER BY rank, length(gloss) LIMIT ?"""

print("verses")
slow = 0.0
for q, expect in [("good shepherd", "Jhn.10.11"), ("beginning God", "Gen.1.1"),
                  ("Jacob's", None), ("faith works", None)]:
    t = time.time()
    r = db.execute(V, (fts(q), 200)).fetchall()
    ms = (time.time() - t) * 1000; slow = max(slow, ms)
    chk(f"{q!r} returns hits", len(r) > 0, len(r))
    if expect:
        chk(f"{q!r} includes {expect}", any(x[0] == expect for x in r), r[:2])
chk("results come back in canonical order",
    [x[0] for x in db.execute(V, (fts("shepherd"), 20))][:1] != [],
    "no hits")
ordered = db.execute(V, (fts("covenant"), 50)).fetchall()
keys = [x[0] for x in ordered]
orders = [db.execute("SELECT book_order, chapter, verse FROM verse WHERE verse_key=?", (k,)).fetchone()
          for k in keys]
chk("Genesis before Revelation", orders == sorted(orders), orders[:3])

print("\nawkward input must not throw")
for q in ["Jacob's", "well-beloved", "", "   ", '"', "a(b", "love OR hate", "*", "NEAR"]:
    try:
        db.execute(V, (fts(q), 20)).fetchall()
        chk(f"{q!r} is handled", True)
    except Exception as e:
        chk(f"{q!r} is handled", False, e)

print("\nnotes")
t = time.time(); r = db.execute(N, (fts("covenant"), 200)).fetchall()
ms = (time.time() - t) * 1000; slow = max(slow, ms)
chk("notes search returns hits", len(r) > 0, len(r))
chk("note text carries no leftover ** markup",
    all("**" not in x[1].replace("**", "") for x in r[:20]))

print("\nlexicon ranking")
t = time.time()
like = "%shepherd%"
r = db.execute(L, (like, like, fts("shepherd"), 60)).fetchall()
ms = (time.time() - t) * 1000; slow = max(slow, ms)
chk("lexicon search returns hits", len(r) > 0, len(r))
chk("the top hit's own gloss is about shepherds",
    r and "shepherd" in r[0][2].lower(), r[0] if r else None)
chk("the Greek for shepherd is near the top",
    any(x[0] == "G4166" for x in r[:8]), [x[0] for x in r[:8]])
chk("'idol' is no longer first", not (r and r[0][0] == "H0457"), r[0] if r else None)

unranked = db.execute(
    "SELECT strongs FROM search_lexicon WHERE search_lexicon MATCH ? LIMIT 1",
    (fts("shepherd"),)).fetchone()
print(f"       (unranked, FTS order, would have answered: {unranked[0]})")

print(f"\nslowest query {slow:.0f} ms")
chk("search stays under 400 ms", slow < 400, f"{slow:.0f} ms")

print()
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURES: {fails}")
sys.exit(1 if fails else 0)
