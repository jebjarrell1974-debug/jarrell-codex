# -*- coding: utf-8 -*-
"""Run-one acceptance test: one token id -> all five layers, both testaments."""
import sqlite3, textwrap
DB="/home/claude/bible/build/bible.db"
db=sqlite3.connect(DB); db.row_factory=sqlite3.Row
PASS=[]; FAIL=[]
def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))

def layers(verse_key, pos, label):
    print(f"\n=== {label}  ({verse_key} word {pos}) " + "="*20)
    t=db.execute("""SELECT * FROM token WHERE verse_key=? AND position=?
                    ORDER BY text_type LIMIT 1""",(verse_key,pos)).fetchone()
    if not t: check(f"{label}: token exists", False); return
    print(f"  surface      {t['surface']}")
    print(f"  translit     {t['translit']}")
    print(f"  gloss        {t['gloss']}")
    check(f"{label}: token exists", True, f"id={t['token_id']}")
    ms=db.execute("""SELECT m.*, c.pos,c.gender,c.number,c.state,c.[case],c.tense,c.voice,c.mood,
                            c.person,c.stem,c.description
                     FROM morpheme m LEFT JOIN morph_code c ON c.code=m.morph_code
                     WHERE m.token_id=? ORDER BY m.seq""",(t['token_id'],)).fetchall()
    check(f"{label}: has morphemes", len(ms)>0, f"{len(ms)} morpheme(s)")
    allparsed=True; alllex=True; conc_ok=True
    for m in ms:
        lex=db.execute("SELECT * FROM lexicon WHERE strongs=?",(m['strongs'],)).fetchone()
        if not lex:
            lex=db.execute("SELECT * FROM lexicon WHERE estrong=?",(m['strongs'],)).fetchone()
        n=db.execute("SELECT COUNT(*) FROM morpheme WHERE strongs=?",(m['strongs'],)).fetchone()[0]
        print(f"   - [{m['seq']}] {m['surface'] or '(joined)'}  {m['strongs']}  {m['morph_code']}")
        print(f"       parsing    {m['description'] or 'MISSING'}")
        print(f"       lexicon    {(lex['lemma']+' = '+lex['gloss']) if lex else 'MISSING'}")
        if lex and lex['definition']:
            print(f"       definition {textwrap.shorten(lex['definition'],110)}")
        print(f"       concordance {n:,} occurrence(s) of {m['strongs']} in the corpus")
        allparsed &= bool(m['description']); alllex &= bool(lex); conc_ok &= n>0
    check(f"{label}: every morpheme parsed", allparsed)
    check(f"{label}: every morpheme has a lexicon entry", alllex)
    check(f"{label}: concordance returns occurrences", conc_ok)
    tv=db.execute("""SELECT code, text FROM translation_verse
                     WHERE canonical_key=? ORDER BY code""",(verse_key,)).fetchall()
    for r in tv: print(f"   {r['code']:6s} {textwrap.shorten(r['text'],100)}")
    check(f"{label}: English translations present", len(tv)>=3, f"{len(tv)} translations")

layers("Gen.1.1",1,"Hebrew - Genesis 1:1 first word")
layers("Jhn.1.1",1,"Greek - John 1:1 first word")

print("\n=== versification " + "="*34)
r=db.execute("""SELECT canonical_key, verse_key FROM translation_verse
                WHERE code='KJV' AND verse_key='2Co.13.14'""").fetchone()
check("KJV 2Co.13:14 maps to the Greek verse key", r and r['canonical_key']=='2Co.13.13',
      f"KJV {r['verse_key']} -> canonical {r['canonical_key']}" if r else "")
n=db.execute("SELECT COUNT(*) FROM translation_verse WHERE canonical_key IS NULL").fetchone()[0]
check("every translation verse resolves to a canonical key", n==0, f"{n} unresolved")
h=db.execute("""SELECT t.alt_ref FROM token t WHERE t.verse_key='Gen.32.1' AND t.alt_ref IS NOT NULL LIMIT 1""").fetchone()
check("Hebrew-vs-English numbering retained on tokens", h is not None,
      f"Gen.32.1 carries Hebrew ref {h['alt_ref']}" if h else "no alt_ref found")

print("\n=== integrity " + "="*38)
for q,label,want in [
  ("SELECT COUNT(*) FROM token","tokens",447744),
  ("SELECT COUNT(*) FROM morpheme","morphemes",None),
  ("SELECT COUNT(*) FROM verse","verses",31219),
  ("SELECT COUNT(*) FROM lexicon","lexicon entries",None),
  ("SELECT COUNT(*) FROM morph_code","morph codes",None)]:
    v=db.execute(q).fetchone()[0]
    print(f"  {label:18s} {v:,}")
    if want: check(f"{label} == {want:,}", v==want)
orph=db.execute("SELECT COUNT(*) FROM morpheme m LEFT JOIN token t ON t.token_id=m.token_id WHERE t.token_id IS NULL").fetchone()[0]
check("no orphan morphemes", orph==0, f"{orph} orphans")
orv=db.execute("SELECT COUNT(*) FROM token t LEFT JOIN verse v ON v.verse_key=t.verse_key WHERE v.verse_key IS NULL").fetchone()[0]
check("no orphan tokens", orv==0, f"{orv} orphans")
unp=db.execute("SELECT COUNT(*) FROM morpheme m LEFT JOIN morph_code c ON c.code=m.morph_code WHERE m.morph_code IS NOT NULL AND c.code IS NULL").fetchone()[0]
check("no unresolved morphology codes", unp==0, f"{unp} unresolved")

print("\n" + "="*56)
print(f"RESULT: {len(PASS)} passed, {len(FAIL)} failed")
if FAIL: print("FAILED:", ", ".join(FAIL))
db.close()
