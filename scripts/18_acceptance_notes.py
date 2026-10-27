# -*- coding: utf-8 -*-
"""Acceptance: the cultural and historical context layer."""
import sqlite3, textwrap
db=sqlite3.connect("/home/claude/bible/build/bible.db"); db.row_factory=sqlite3.Row
P=[];F=[]
def ck(n,ok,d=""):
    (P if ok else F).append(n); print(f"  [{'PASS' if ok else 'FAIL'}] {n}"+(f"  {d}" if d else ""))
one=lambda q,*p: db.execute(q,p).fetchone()[0]

print("=== coverage " + "="*38)
n=one("SELECT COUNT(*) FROM note")
ck("notes loaded", n>100000, f"{n:,} notes")
b=one("SELECT COUNT(DISTINCT book) FROM note")
ck("every book of the canon covered", b==66, f"{b} books")
cov=one("SELECT COUNT(DISTINCT verse_key) FROM note WHERE verse_key IS NOT NULL")
tot=one("SELECT COUNT(*) FROM verse")
ck("most verses carry at least one note", cov/tot>0.9, f"{cov:,}/{tot:,} verses ({100*cov/tot:.1f}%)")

print("\n=== integrity " + "="*37)
orph=one("""SELECT COUNT(*) FROM note n WHERE n.verse_key IS NOT NULL
             AND NOT EXISTS(SELECT 1 FROM verse v WHERE v.verse_key=n.verse_key)""")
ck("every verse note resolves to a canonical verse", orph==0, f"{orph} unresolved")
empty=one("SELECT COUNT(*) FROM note WHERE body IS NULL OR trim(body)=''")
ck("no empty notes", empty==0, f"{empty} empty")
nosrc=one("SELECT COUNT(*) FROM note WHERE source IS NULL OR source=''")
ck("every note records its source", nosrc==0, f"{nosrc} missing")

print("\n=== shape " + "="*41)
intros=one("SELECT COUNT(*) FROM note WHERE kind='book_intro'")
ck("book introductions kept separate from verse notes", intros==66, f"{intros} book intros")
ch=one("SELECT COUNT(*) FROM note WHERE kind='chapter_intro'")
ck("chapter introductions kept separate", ch>1000, f"{ch:,} chapter intros")
q=one("SELECT COUNT(*) FROM note WHERE quote IS NOT NULL")
ck("notes carry the original-language words they discuss", q>100000, f"{q:,} with a quote")
leak=one("SELECT COUNT(*) FROM note WHERE body LIKE '%rc://%'")
ck("internal rc:// links cleaned out of note text", leak==0, f"{leak} remaining")

print("\n=== it actually reads " + "="*29)
r=db.execute("""SELECT quote, category, body FROM note
                WHERE verse_key='Act.17.22' AND category='figs-metonymy' LIMIT 1""").fetchone()
ck("Acts 17:22 explains the Areopagus by name",
   r is not None and "Areopagus" in (r["body"] or ""),
   textwrap.shorten(r["body"], 80) if r else "")
g=db.execute("SELECT body FROM note WHERE verse_key='Gen.1.1' LIMIT 1").fetchone()
ck("Genesis 1:1 carries a substantive note", g and len(g["body"])>200, f"{len(g['body'])} chars" if g else "")

print("\n=== licence " + "="*39)
sa=one("SELECT COUNT(*) FROM note WHERE source LIKE '%CC BY-SA%'")
ck("share-alike licence recorded on every note", sa==n, f"{sa:,}/{n:,}")

print("\n" + "="*56)
print(f"RESULT: {len(P)} passed, {len(F)} failed")
if F: print("FAILED:", ", ".join(F))
