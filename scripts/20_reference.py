# -*- coding: utf-8 -*-
"""Reference parsing: turn what a person types into a canonical verse key.

"Jn 3:16", "john 3 16", "1 cor 13", "Ps 23", "Genesis 1:1-5" all have to work.
Lives in the database as a name table plus this reference implementation, so
the Android client can port the same rules instead of inventing its own.
"""
import re, sqlite3, sys
DB="/home/claude/bible/build/bible.db"
db=sqlite3.connect(DB)

NAMES={r[0].lower(): r[1] for r in db.execute("SELECT name, book FROM book_name")}

# "1 cor 13:4-7" -> book "1 cor", chapter 13, verse 4, end 7
REF=re.compile(r"""^\s*
  (?P<book>(?:[1-3]\s*)?[A-Za-z][A-Za-z\s.]*?)\s*\.?\s*
  (?P<chapter>\d+)
  (?:\s*[:.\s]\s*(?P<verse>\d+))?
  (?:\s*-\s*(?P<end>\d+))?
\s*$""", re.X)

def parse(text):
    """-> (book, chapter, verse|None, end|None) or None."""
    if not text: return None
    m=REF.match(text.replace("–","-").replace("—","-"))
    if not m: return None
    raw=re.sub(r"[\s.]+"," ",m.group("book")).strip().lower()
    book=NAMES.get(raw) or NAMES.get(raw.replace(" ",""))
    if not book:
        # "1john" / "1 john" and the like
        mm=re.match(r"^([1-3])\s*(.+)$", raw)
        if mm: book=NAMES.get(f"{mm.group(1)} {mm.group(2)}")
    if not book: return None
    ch=int(m.group("chapter"))
    vs=int(m.group("verse")) if m.group("verse") else None
    end=int(m.group("end")) if m.group("end") else None
    return (book, ch, vs, end)

def resolve(text):
    """-> list of canonical verse keys that actually exist."""
    p=parse(text)
    if not p: return []
    book, ch, vs, end = p
    if vs is None:
        return [r[0] for r in db.execute(
            "SELECT verse_key FROM verse WHERE book=? AND chapter=? ORDER BY verse",(book,ch))]
    lo, hi = vs, (end or vs)
    return [r[0] for r in db.execute(
        "SELECT verse_key FROM verse WHERE book=? AND chapter=? AND verse BETWEEN ? AND ? ORDER BY verse",
        (book,ch,lo,hi))]

if __name__ == "__main__":
    CASES=[("Jn 3:16","Jhn.3.16"),("john 3 16","Jhn.3.16"),("John 3:16","Jhn.3.16"),
           ("1 cor 13:4","1Co.13.4"),("1cor 13:4","1Co.13.4"),("I Corinthians 13:4","1Co.13.4"),
           ("Ps 23:1","Psa.23.1"),("Psalm 23:1","Psa.23.1"),("Gen 1:1","Gen.1.1"),
           ("genesis 1.1","Gen.1.1"),("Rev 22:21","Rev.22.21"),("Song 2:1","Sng.2.1"),
           ("2 Kgs 5:12","2Ki.5.12"),("Mt 5:3","Mat.5.3"),("Acts 17:22","Act.17.22"),
           ("3 John 1:4","3Jn.1.4"),("Phil 4:13","Php.4.13")]
    ok=bad=0
    for text, want in CASES:
        got=resolve(text)
        hit = got and got[0]==want
        ok, bad = (ok+1, bad) if hit else (ok, bad+1)
        if not hit: print(f"  FAIL  {text!r} -> {got[:1] or 'nothing'}  (wanted {want})")
    print(f"single references: {ok}/{len(CASES)} correct")
    rng=resolve("Genesis 1:1-5"); print(f"range  'Genesis 1:1-5' -> {len(rng)} verses {rng[:2]}...")
    cha=resolve("Psalm 23");      print(f"chapter 'Psalm 23'     -> {len(cha)} verses (7: Hebrew superscription is verse 0)")
    non=resolve("Hezekiah 3:1");  print(f"nonexistent book       -> {non}")
    oob=resolve("Gen 99:1");      print(f"out-of-range chapter   -> {oob}")
    sys.exit(0 if bad==0 and len(rng)==5 and len(cha)==7 and not non and not oob else 1)
