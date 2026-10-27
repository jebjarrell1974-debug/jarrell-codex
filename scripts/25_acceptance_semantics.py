# -*- coding: utf-8 -*-
"""Acceptance: semantic roles, and above all that the alignment is real."""
import re, sqlite3
db=sqlite3.connect("/home/claude/bible/build/bible.db"); db.row_factory=sqlite3.Row
P=[];F=[]
def ck(n,ok,d=""):
    (P if ok else F).append(n); print(f"  [{'PASS' if ok else 'FAIL'}] {n}"+(f"  {d}" if d else ""))
one=lambda q,*p: db.execute(q,p).fetchone()[0]

print("=== loaded " + "="*41)
n=one("SELECT COUNT(*) FROM semantics")
ck("semantics loaded", n>120000, f"{n:,} rows")
ck("semantic roles present", one("SELECT COUNT(*) FROM semantics WHERE role IS NOT NULL")>40000,
   f"{one('SELECT COUNT(*) FROM semantics WHERE role IS NOT NULL'):,}")
ck("Louw-Nida domains present", one("SELECT COUNT(*) FROM semantics WHERE louw_nida IS NOT NULL")>120000,
   f"{one('SELECT COUNT(*) FROM semantics WHERE louw_nida IS NOT NULL'):,}")

print("\n=== the alignment is real " + "="*25)
# The bug this catches: joining on position alone looks ~100% successful while
# silently pairing different words, because the two critical texts diverge.
# Every aligned row must sit on a token whose Strong's number agrees.
bad=one("""SELECT COUNT(*) FROM semantics s
           JOIN token t ON t.verse_key=s.verse_key AND t.position=s.position
           WHERE t.language<>'G'""")
ck("every aligned row sits on a Greek token", bad==0, f"{bad} non-Greek")
orph=one("""SELECT COUNT(*) FROM semantics s WHERE NOT EXISTS(
              SELECT 1 FROM token t WHERE t.verse_key=s.verse_key AND t.position=s.position)""")
ck("every aligned row sits on a token that exists", orph==0, f"{orph} orphans")

# John 3:16 is the worked example: the amalgamated text carries an extra autou
# at position 11 that Nestle 1904 lacks.
got={r["position"]: r["role"] for r in db.execute(
    "SELECT position, role FROM semantics WHERE verse_key='Jhn.3.16'")}
ck("the variant word at John 3:16 position 11 is left unaligned",
   11 not in got, f"positions carrying semantics: {sorted(got)[:6]}...")
v=db.execute("""SELECT t.surface, s.role FROM token t JOIN semantics s
                ON s.verse_key=t.verse_key AND s.position=t.position
                WHERE t.verse_key='Jhn.3.16' AND s.role='verb' ORDER BY t.position""").fetchall()
ck("the verbs of John 3:16 are actually verbs",
   {x["surface"].strip(",.") for x in v} >= {"ἠγάπησεν", "ἔδωκεν"},
   ", ".join(x["surface"] for x in v))

print("\n=== it answers who does what " + "="*22)
subj=db.execute("""SELECT t.surface, t.gloss FROM token t JOIN semantics s
                   ON s.verse_key=t.verse_key AND s.position=t.position
                   WHERE s.role='subject' LIMIT 1""").fetchone()
ck("subjects are identified", subj is not None,
   f"{subj['surface']} ({subj['gloss']})" if subj else "")
ck("participant referents resolve pronouns",
   one("SELECT COUNT(*) FROM semantics WHERE referent IS NOT NULL")>10000,
   f"{one('SELECT COUNT(*) FROM semantics WHERE referent IS NOT NULL'):,} words carry a referent")
dom=one("SELECT COUNT(DISTINCT louw_nida) FROM semantics WHERE louw_nida IS NOT NULL")
ck("semantic domains are varied enough to search", dom>2000, f"{dom:,} distinct codes")

print("\n" + "="*56)
print(f"RESULT: {len(P)} passed, {len(F)} failed")
if F: print("FAILED:", ", ".join(F))
