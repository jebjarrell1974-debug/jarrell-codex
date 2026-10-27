# -*- coding: utf-8 -*-
"""Acceptance: search, references, cross-references, full lexicon, proper names."""
import sqlite3, sys, time
sys.path.insert(0,"/home/claude/bible/scripts")
db=sqlite3.connect("/home/claude/bible/build/bible.db"); db.row_factory=sqlite3.Row
P=[];F=[]
def ck(n,ok,d=""):
    (P if ok else F).append(n); print(f"  [{'PASS' if ok else 'FAIL'}] {n}"+(f"  {d}" if d else ""))
one=lambda q,*p: db.execute(q,p).fetchone()[0]

print("=== search " + "="*41)
ck("verse text indexed", one("SELECT COUNT(*) FROM search_verse")>120000,
   f"{one('SELECT COUNT(*) FROM search_verse'):,} rows")
ck("notes indexed", one("SELECT COUNT(*) FROM search_note")>100000)
ck("lexicon indexed", one("SELECT COUNT(*) FROM search_lexicon")>20000)
r=db.execute("""SELECT verse_key FROM search_verse WHERE search_verse MATCH ? AND code='KJV'""",
             ('"the LORD is my shepherd"',)).fetchall()
ck("phrase search finds Psalm 23:1", any(x["verse_key"]=="Psa.23.1" for x in r),
   ", ".join(x["verse_key"] for x in r[:3]))
t=time.perf_counter()
db.execute("SELECT verse_key FROM search_verse WHERE search_verse MATCH 'love' LIMIT 200").fetchall()
ms=(time.perf_counter()-t)*1000
ck("search is fast enough for typing", ms<200, f"{ms:.1f} ms for a common word")

print("\n=== typed references " + "="*31)
import importlib.util
spec=importlib.util.spec_from_file_location("ref","/home/claude/bible/scripts/20_reference.py")
ref=importlib.util.module_from_spec(spec)
sys.argv=["x"]
try: spec.loader.exec_module(ref)
except SystemExit: pass
ck("'Jn 3:16' resolves", ref.resolve("Jn 3:16")[:1]==["Jhn.3.16"])
ck("'1 cor 13' returns a whole chapter", len(ref.resolve("1 cor 13"))>=13,
   f"{len(ref.resolve('1 cor 13'))} verses")
ck("a made-up book returns nothing", ref.resolve("Hezekiah 3:1")==[])
ck("book names and abbreviations stored", one("SELECT COUNT(*) FROM book_name")>200,
   f"{one('SELECT COUNT(*) FROM book_name')} names")

print("\n=== cross-references " + "="*31)
n=one("SELECT COUNT(*) FROM xref")
ck("cross-references loaded", n>400000, f"{n:,}")
ck("most verses have one", one("SELECT COUNT(DISTINCT from_key) FROM xref")>29000,
   f"{one('SELECT COUNT(DISTINCT from_key) FROM xref'):,} verses")
top=db.execute("SELECT to_key FROM xref WHERE from_key='Jhn.3.16' ORDER BY votes DESC LIMIT 1").fetchone()
ck("ranking puts a sensible verse first for John 3:16", top and top["to_key"]=="Rom.5.8",
   top["to_key"] if top else "none")
orph=one("""SELECT COUNT(*) FROM xref x WHERE NOT EXISTS
            (SELECT 1 FROM verse v WHERE v.verse_key=x.from_key)""")
ck("source verses resolve", orph<100, f"{orph} unresolved")

print("\n=== full lexicon " + "="*35)
ck("full LSJ loaded", one("SELECT COUNT(*) FROM lexicon_full")>9000,
   f"{one('SELECT COUNT(*) FROM lexicon_full'):,} entries")
ck("full entries are substantially longer than the brief ones",
   one("SELECT AVG(length(entry)) FROM lexicon_full") > 3*one("SELECT AVG(length(definition)) FROM lexicon"),
   f"{one('SELECT CAST(AVG(length(entry)) AS INT) FROM lexicon_full')} vs "
   f"{one('SELECT CAST(AVG(length(definition)) AS INT) FROM lexicon')} chars")
# LSJ uses angle brackets editorially - <kappa>pelos marks restored text - so a
# bare "<" is content, not markup. Test for actual HTML tags and script only.
import re as _re
_tag=_re.compile(r'</?[a-zA-Z][a-zA-Z0-9]*(\s[^>]*)?/?>')
_bad=sum(1 for (e,) in db.execute("SELECT entry FROM lexicon_full")
         if e and (_tag.search(e) or "javascript" in e.lower()))
ck("HTML tags and script scrubbed from entries", _bad==0, f"{_bad} remaining")
_ed=one("SELECT COUNT(*) FROM lexicon_full WHERE entry LIKE '%<%'")
ck("editorial angle brackets preserved as content", _ed>0, f"{_ed} entries keep them")

print("\n=== proper names " + "="*35)
ck("proper names loaded", one("SELECT COUNT(*) FROM proper_name")>4000,
   f"{one('SELECT COUNT(*) FROM proper_name'):,} individuals and places")
ck("name references loaded", one("SELECT COUNT(*) FROM proper_name_ref")>40000,
   f"{one('SELECT COUNT(*) FROM proper_name_ref'):,}")
marys=one("SELECT COUNT(*) FROM proper_name WHERE name='Mary'")
ck("the different Marys are separate people", marys>=5, f"{marys} distinct")
mother=db.execute("""SELECT COUNT(*) FROM proper_name_ref
                     WHERE unified LIKE 'Mary@Mat.1.16%'""").fetchone()[0]
ck("Jesus' mother has her own reference list", mother>0, f"{mother} verses")

print("\n" + "="*56)
print(f"RESULT: {len(P)} passed, {len(F)} failed")
if F: print("FAILED:", ", ".join(F))
