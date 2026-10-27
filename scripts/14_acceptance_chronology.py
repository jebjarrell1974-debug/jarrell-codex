# -*- coding: utf-8 -*-
"""Acceptance: chronology is selectable, attributed, and never silently borrowed."""
import sqlite3, textwrap
DB="/home/claude/bible/build/bible.db"
db=sqlite3.connect(DB); db.row_factory=sqlite3.Row
P=[];F=[]
def ck(n,ok,d=""):
    (P if ok else F).append(n); print(f"  [{'PASS' if ok else 'FAIL'}] {n}"+(f"  {d}" if d else ""))
yr=lambda v: "—" if v is None else (f"{abs(v)} BC" if v<0 else f"AD {v}")

print("=== schemes " + "="*40)
n=db.execute("SELECT COUNT(*) FROM chronology_scheme").fetchone()[0]
ck("multiple schemes exist", n>=4, f"{n} schemes")
d=db.execute("SELECT scheme_id FROM chronology_scheme WHERE is_default=1").fetchall()
ck("exactly one default scheme", len(d)==1, d[0]['scheme_id'] if d else "none")
nosrc=db.execute("SELECT COUNT(*) FROM chronology_scheme WHERE source IS NULL OR source=''").fetchone()[0]
ck("every scheme cites a source", nosrc==0, f"{nosrc} missing")

print("\n=== coverage honesty " + "="*31)
bad=[]
for r in db.execute("""SELECT s.scheme_id, s.coverage,
                         (SELECT COUNT(*) FROM event_date d WHERE d.scheme_id=s.scheme_id) n
                       FROM chronology_scheme s"""):
    if r['coverage']=='none' and r['n']>0: bad.append(f"{r['scheme_id']} claims none but has {r['n']}")
    if r['coverage']=='anchors' and r['n']==0: bad.append(f"{r['scheme_id']} claims anchors but has 0")
    if r['coverage']=='full' and r['n']<400: bad.append(f"{r['scheme_id']} claims full but has {r['n']}")
ck("declared coverage matches actual data", not bad, "; ".join(bad))

print("\n=== no silent borrowing " + "="*28)
# The whole point: a scheme with no date must return NULL, not another scheme's year.
rows=db.execute("""SELECT scheme_id, start_year FROM event_in_scheme WHERE event_id=1""").fetchall()
have={r['scheme_id']: r['start_year'] for r in rows}
ck("a scheme without a date returns NULL", have.get('thiele') is None and have.get('septuagint') is None,
   f"thiele={have.get('thiele')}, septuagint={have.get('septuagint')}")
ck("schemes that do have a date disagree, and both are shown",
   have.get('jones')==-4003 and have.get('ussher')==-4004,
   f"Jones {yr(have.get('jones'))} vs Ussher {yr(have.get('ussher'))}")

print("\n=== the 43-year disagreement " + "="*22)
k=db.execute("""SELECT scheme_id, start_year FROM event_in_scheme WHERE event_id=163""").fetchall()
kk={r['scheme_id']: r['start_year'] for r in k}
ck("division of the kingdom differs by 43 years",
   kk.get('jones')==-974 and kk.get('thiele')==-931,
   f"Jones {yr(kk.get('jones'))} vs Thiele {yr(kk.get('thiele'))}")

print("\n=== provenance " + "="*37)
noprec=db.execute("SELECT COUNT(*) FROM event_date WHERE precision IS NULL").fetchone()[0]
ck("every date records how certain it is", noprec==0, f"{noprec} missing")
der=db.execute("SELECT COUNT(*) FROM event_date WHERE precision='derived'").fetchone()[0]
ck("derived dates are marked as derived, not stated", der>0, f"{der} derived")

print("\n=== the explainer " + "="*34)
notes=db.execute("SELECT heading, length(body) b FROM chronology_note ORDER BY sort_order").fetchall()
ck("explainer notes exist", len(notes)>=4, f"{len(notes)} notes")
ck("every note has real content", all(r['b']>200 for r in notes),
   ", ".join(f"{r['heading']} ({r['b']}c)" for r in notes))

print("\n=== what a reader sees " + "="*29)
print("  Division of the kingdom:")
for r in db.execute("""SELECT scheme_name, start_year, note FROM event_in_scheme
                       WHERE event_id=163 ORDER BY scheme_id"""):
    print(f"    {r['scheme_name'][:30]:32s} {yr(r['start_year']):>10s}  {textwrap.shorten(r['note'] or '', 44)}")

print("\n" + "="*56)
print(f"RESULT: {len(P)} passed, {len(F)} failed")
if F: print("FAILED:", ", ".join(F))
db.close()
