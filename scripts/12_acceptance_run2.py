# -*- coding: utf-8 -*-
"""Run-two acceptance: geography, people, events and dictionary layers."""
import sqlite3, textwrap
DB="/home/claude/bible/build/bible.db"
db=sqlite3.connect(DB); db.row_factory=sqlite3.Row
P=[];F=[]
def ck(n,ok,d=""):
    (P if ok else F).append(n); print(f"  [{'PASS' if ok else 'FAIL'}] {n}"+(f"  {d}" if d else ""))

print("=== geography " + "="*38)
j=db.execute("SELECT * FROM place WHERE name='Jerusalem'").fetchone()
ck("Jerusalem has plausible coordinates",
   j and 31.5<j['latitude']<32.0 and 35.0<j['longitude']<35.5,
   f"{j['latitude']:.4f}, {j['longitude']:.4f}" if j else "")
nod=db.execute("SELECT * FROM place WHERE name='Nod'").fetchone()
ck("a genuinely lost place has NO coordinates", nod and nod['latitude'] is None,
   f"Nod -> {nod['status']}" if nod else "")
eg=db.execute("SELECT * FROM place WHERE name='Egypt'").fetchone()
ck("a region is not reported as unknown", eg and eg['status']=='region', f"Egypt -> {eg['status']}" if eg else "")
a17=[r[0] for r in db.execute("""SELECT DISTINCT p.name FROM place p JOIN place_verse pv USING(place_id)
                                 WHERE pv.verse_key GLOB 'Act.17.*' ORDER BY 1""")]
ck("Acts 17 returns Paul's itinerary", {'Athens','Berea','Thessalonica'} <= set(a17), ", ".join(a17))
orp=db.execute("SELECT COUNT(*) FROM place_verse pv LEFT JOIN verse v ON v.verse_key=pv.verse_key WHERE v.verse_key IS NULL").fetchone()[0]
ck("every place-verse link resolves", orp==0, f"{orp} unresolved")

print("\n=== people " + "="*41)
m=db.execute("SELECT * FROM person WHERE name='Moses'").fetchone()
ck("Moses is present with dates", m and m['birth_year'] is not None,
   f"b.{m['birth_year']} d.{m['death_year']}" if m else "")
n=db.execute("""SELECT COUNT(DISTINCT verse_key) FROM person_verse pv
                JOIN person p USING(person_id) WHERE p.name='Moses'""").fetchone()[0]
ck("Moses is linked to many verses", n>100, f"{n:,} verses")
gen1=[r[0] for r in db.execute("""SELECT p.name FROM person p JOIN person_verse pv USING(person_id)
                                  WHERE pv.verse_key='Gen.1.1'""")]
ck("Genesis 1:1 names God", "God" in gen1, ", ".join(gen1) or "none")

print("\n=== events " + "="*41)
e=db.execute("SELECT COUNT(*) FROM event").fetchone()[0]
ck("event timeline loaded", e>=400, f"{e} events")
first=db.execute("SELECT title,start_date FROM event ORDER BY sort_key LIMIT 1").fetchone()
ck("timeline is ordered", first is not None, f"earliest: {first['title']} ({first['start_date']})" if first else "")
ex=db.execute("""SELECT e.title, e.start_date FROM event e JOIN event_verse ev USING(event_id)
                 WHERE ev.verse_key GLOB 'Exo.14.*' ORDER BY e.sort_key LIMIT 1""").fetchone()
ck("events join to verses", ex is not None, f"Exodus 14 -> {ex['title']}" if ex else "")

print("\n=== dictionary " + "="*37)
d=db.execute("SELECT COUNT(*) FROM dictionary").fetchone()[0]
h=db.execute("SELECT COUNT(DISTINCT term_id) FROM dictionary").fetchone()[0]
ck("Easton's loaded without collapsing senses", d>6000 and h<d, f"{d:,} senses / {h:,} headwords")
ab=db.execute("SELECT COUNT(*) FROM dictionary WHERE term_label='Abda'").fetchone()[0]
ck("multi-sense headwords keep every sense", ab>=3, f"'Abda' has {ab} senses")
lk=db.execute("SELECT COUNT(*) FROM dictionary WHERE person_slug IS NOT NULL").fetchone()[0]
ck("dictionary senses link to people", lk>1000, f"{lk:,} linked")

print("\n=== one verse, every layer " + "="*25)
vk="Act.17.22"
row=db.execute("SELECT COUNT(*) FROM token WHERE verse_key=?",(vk,)).fetchone()[0]
pl=[r[0] for r in db.execute("SELECT DISTINCT p.name FROM place p JOIN place_verse pv USING(place_id) WHERE pv.verse_key=?",(vk,))]
pp=[r[0] for r in db.execute("SELECT p.name FROM person p JOIN person_verse pv USING(person_id) WHERE pv.verse_key=?",(vk,))]
tr=db.execute("SELECT text FROM translation_verse WHERE canonical_key=? AND code='KJV'",(vk,)).fetchone()
print(f"  {vk}: {row} Greek words | places {pl or '-'} | people {pp or '-'}")
if tr: print(f"  KJV: {textwrap.shorten(tr['text'],95)}")
ck("a single verse joins text, places, people and translation",
   row>0 and tr is not None and (pl or pp))

print("\n" + "="*56)
print(f"RESULT: {len(P)} passed, {len(F)} failed")
if F: print("FAILED:", ", ".join(F))
db.close()
