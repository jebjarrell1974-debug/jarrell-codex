# -*- coding: utf-8 -*-
"""MACULA Greek semantics, aligned by CONTENT rather than by position.

Answers what morphology cannot: who does what to whom, which "he" is meant,
and which words share a Louw-Nida semantic domain.

The hard part is the join. MACULA follows Nestle 1904; this project follows the
amalgamated text, which also carries Byzantine and Textus Receptus readings. So
word positions drift apart the moment a verse contains a variant: John 3:16 has
an extra autou at position 11 in the amalgamated text, and every later word in
that verse is off by one. Joining on position therefore looks successful while
being silently wrong - it proves a token exists at that index, not that it is
the same word.

This aligns each verse by Strong's number using a longest-common-subsequence
walk, and keeps only matches where the Strong's numbers agree. Words present in
one text and not the other are left unjoined and counted, which is the honest
outcome: they are real textual differences, not failures.
"""
import csv, re, sqlite3, collections
DB="/home/claude/bible/build/bible.db"
SRC="/home/claude/bible/sources/macula-greek/Nestle1904/tsv/macula-greek-Nestle1904.tsv"
USFM={"MAT":"Mat","MRK":"Mrk","LUK":"Luk","JHN":"Jhn","ACT":"Act","ROM":"Rom","1CO":"1Co",
"2CO":"2Co","GAL":"Gal","EPH":"Eph","PHP":"Php","COL":"Col","1TH":"1Th","2TH":"2Th",
"1TI":"1Ti","2TI":"2Ti","TIT":"Tit","PHM":"Phm","HEB":"Heb","JAS":"Jas","1PE":"1Pe",
"2PE":"2Pe","1JN":"1Jn","2JN":"2Jn","3JN":"3Jn","JUD":"Jud","REV":"Rev"}
ROLE={"s":"subject","v":"verb","o":"object","o2":"second object","io":"indirect object",
      "p":"predicate","adv":"adverbial","aux":"auxiliary","apposition":"apposition"}
REF=re.compile(r'^([A-Z1-3]{3})\s+(\d+):(\d+)!(\d+)$')
num=lambda s: int(re.sub(r'\D','',s or '0') or 0)

def lcs_pairs(a, b):
    """Index pairs where a[i]==b[j], as a longest common subsequence."""
    n, m = len(a), len(b)
    if not n or not m: return []
    # width-limited DP: verses are short, so the full table is cheap
    dp=[[0]*(m+1) for _ in range(n+1)]
    for i in range(n-1, -1, -1):
        for j in range(m-1, -1, -1):
            dp[i][j] = dp[i+1][j+1]+1 if a[i]==b[j] else max(dp[i+1][j], dp[i][j+1])
    out=[]; i=j=0
    while i<n and j<m:
        if a[i]==b[j]: out.append((i,j)); i+=1; j+=1
        elif dp[i+1][j] >= dp[i][j+1]: i+=1
        else: j+=1
    return out

db=sqlite3.connect(DB)
db.executescript("""
DROP TABLE IF EXISTS semantics;
CREATE TABLE semantics(
  verse_key TEXT NOT NULL,
  position  INT  NOT NULL,       -- position in THIS project's text
  role      TEXT, role_code TEXT, word_class TEXT,
  frame     TEXT, referent TEXT, subj_ref TEXT,
  domain    TEXT, louw_nida TEXT,
  PRIMARY KEY(verse_key, position));
""")

# MACULA rows, grouped by verse
mac=collections.defaultdict(list); unmapped=collections.Counter()
with open(SRC, encoding="utf-8", newline="") as fh:
    for r in csv.DictReader(fh, delimiter="\t", quoting=csv.QUOTE_NONE):
        m=REF.match((r.get("ref") or "").strip())
        if not m: unmapped[(r.get("ref") or "")[:10]]+=1; continue
        bk=USFM.get(m.group(1))
        if not bk: unmapped[m.group(1)]+=1; continue
        mac[f"{bk}.{m.group(2)}.{m.group(3)}"].append((int(m.group(4)), r))
for v in mac.values(): v.sort(key=lambda x: x[0])

# Our Greek tokens, grouped by verse
ours=collections.defaultdict(list)
for vk, pos, simple in db.execute("""
        SELECT t.verse_key, t.position, m.strongs_simple
        FROM token t JOIN morpheme m ON m.token_id=t.token_id AND m.seq=0
        WHERE t.language='G' AND t.text_type GLOB '*N*'
        ORDER BY t.verse_key, t.position"""):
    ours[vk].append((pos, num(simple)))

rows=[]; stats=collections.Counter()
for vk, mrows in mac.items():
    mine=ours.get(vk)
    if not mine: stats["verse_missing_here"]+=len(mrows); continue
    a=[num(r.get("strong")) for _, r in mrows]
    b=[s for _, s in mine]
    pairs=lcs_pairs(a, b)
    stats["aligned"]+=len(pairs)
    stats["macula_unmatched"]+=len(a)-len(pairs)
    stats["ours_unmatched"]+=len(b)-len(pairs)
    for mi, oi in pairs:
        r=mrows[mi][1]; pos=mine[oi][0]
        code=(r.get("role") or "").strip() or None
        rows.append((vk, pos, ROLE.get(code, code), code,
                     (r.get("class") or "").strip() or None,
                     (r.get("frame") or "").strip() or None,
                     (r.get("referent") or "").strip() or None,
                     (r.get("subjref") or "").strip() or None,
                     (r.get("domain") or "").strip() or None,
                     (r.get("ln") or "").strip() or None))

db.executemany("INSERT OR IGNORE INTO semantics VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
db.executescript("""
CREATE INDEX IF NOT EXISTS ix_sem_verse ON semantics(verse_key, position);
CREATE INDEX IF NOT EXISTS ix_sem_role  ON semantics(role);
CREATE INDEX IF NOT EXISTS ix_sem_ln    ON semantics(louw_nida);
""")
db.commit()
one=lambda q,*p: db.execute(q,p).fetchone()[0]
total=sum(len(v) for v in mac.values())
print(f"MACULA rows:        {total:,}")
print(f"aligned by content: {stats['aligned']:,} ({100*stats['aligned']/total:.2f}%)")
print(f"  in MACULA only (N1904 readings we do not carry): {stats['macula_unmatched']:,}")
print(f"  in ours only (Byzantine/TR readings N1904 lacks): {stats['ours_unmatched']:,}")
print(f"semantics rows:     {one('SELECT COUNT(*) FROM semantics'):,}")
print(f"  with a role:      {one('SELECT COUNT(*) FROM semantics WHERE role IS NOT NULL'):,}")
print(f"  with Louw-Nida:   {one('SELECT COUNT(*) FROM semantics WHERE louw_nida IS NOT NULL'):,}")
print(f"  with a referent:  {one('SELECT COUNT(*) FROM semantics WHERE referent IS NOT NULL'):,}")
print("\nJohn 3:16, aligned:")
for r in db.execute("""SELECT t.position, t.surface, t.gloss, s.role
                       FROM token t JOIN semantics s
                         ON s.verse_key=t.verse_key AND s.position=t.position
                       WHERE t.verse_key='Jhn.3.16' ORDER BY t.position LIMIT 14"""):
    print(f"   {r[0]:>2}  {r[1]:<13} {str(r[2])[:20]:<22} {r[3] or ''}")
db.close()
