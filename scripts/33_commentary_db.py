#!/usr/bin/env python3
"""Build commentary.db as a separate file the clients can attach.

Kept out of bible.db on purpose. The core database is already 456 MB and
compresses to 133 MB, which is what an Android install has to carry.
Commentary adds another 44 MB compressed, and it is the one layer a reader
can comfortably live without on a phone with no room. Separate file means
the client ships the text, the parsing, the lexicons, the places and the
notes, and fetches the commentators only if the reader wants them.

ATTACH 'commentary.db' AS cm;  then join on verse_key as usual.
"""
import json, glob, os, sqlite3, sys

OUT   = '/home/claude/site/data'
DEST  = 'build/commentary.db'

if os.path.exists(DEST): os.remove(DEST)
c = sqlite3.connect(DEST)
c.executescript("""
PRAGMA journal_mode = OFF;
PRAGMA synchronous  = OFF;

CREATE TABLE commentator (
  source_id TEXT PRIMARY KEY,
  author    TEXT NOT NULL,
  work      TEXT NOT NULL,
  sort      INTEGER NOT NULL
);

CREATE TABLE commentary (
  unit_id    INTEGER PRIMARY KEY,
  source_id  TEXT NOT NULL REFERENCES commentator(source_id),
  book       TEXT NOT NULL,
  chapter    INTEGER NOT NULL,
  -- NULL verses mean the unit covers the whole chapter, or the whole book
  verse_from INTEGER,
  verse_to   INTEGER,
  scope      TEXT NOT NULL,          -- book | chapter | passage
  title      TEXT,
  body       TEXT NOT NULL           -- paragraphs joined with a blank line
);

-- one row per verse a unit covers, so a verse lookup is a plain index hit
CREATE TABLE commentary_verse (
  unit_id   INTEGER NOT NULL REFERENCES commentary(unit_id),
  verse_key TEXT NOT NULL
);
""")

meta = json.load(open(f'{OUT}/commentary.json', encoding='utf-8'))
for i, sid in enumerate(meta['order']):
    a, w = meta['sources'][sid]
    c.execute("INSERT INTO commentator VALUES (?,?,?,?)", (sid, a, w, i))

uid = 0
rows, vrows = [], []
for p in sorted(glob.glob(f'{OUT}/cm/*.json')):
    d = json.load(open(p, encoding='utf-8'))
    book, ch = d['b'], d['c']
    for sid, kind, title, v1, v2, paras in d['u']:
        uid += 1
        rows.append((uid, sid, book, ch, v1, v2, kind, title,
                     '\n\n'.join(paras)))
        if v1 is not None:
            for v in range(v1, (v2 or v1) + 1):
                vrows.append((uid, f'{book}.{ch}.{v}'))
    if len(rows) > 20000:
        c.executemany("INSERT INTO commentary VALUES (?,?,?,?,?,?,?,?,?)", rows)
        c.executemany("INSERT INTO commentary_verse VALUES (?,?)", vrows)
        rows, vrows = [], []
c.executemany("INSERT INTO commentary VALUES (?,?,?,?,?,?,?,?,?)", rows)
c.executemany("INSERT INTO commentary_verse VALUES (?,?)", vrows)

c.executescript("""
CREATE INDEX ix_cm_chapter ON commentary(book, chapter);
CREATE INDEX ix_cm_source  ON commentary(source_id);
CREATE INDEX ix_cmv_verse  ON commentary_verse(verse_key);
CREATE INDEX ix_cmv_unit   ON commentary_verse(unit_id);
""")
c.commit()
c.execute("VACUUM")
c.commit()

n_u  = c.execute("select count(*) from commentary").fetchone()[0]
n_v  = c.execute("select count(*) from commentary_verse").fetchone()[0]
n_dv = c.execute("select count(distinct verse_key) from commentary_verse").fetchone()[0]
w    = c.execute("select sum(length(body)) from commentary").fetchone()[0]
print(f"units            {n_u:>10,}")
print(f"verse links      {n_v:>10,}")
print(f"distinct verses  {n_dv:>10,}")
print(f"characters       {w:>10,}")
for sid, a, n in c.execute("""select c.source_id, m.author, count(*)
                              from commentary c join commentator m
                                on m.source_id = c.source_id
                              group by c.source_id order by m.sort"""):
    print(f"  {a:<22} {n:>7,}")
print(f"\nfile  {os.path.getsize(DEST)/1048576:.0f} MB")

# a lookup has to actually work before this ships
q = """select m.author, c.scope, c.verse_from, c.verse_to, substr(c.body,1,60)
       from commentary_verse v
       join commentary c  on c.unit_id = v.unit_id
       join commentator m on m.source_id = c.source_id
       where v.verse_key = 'Jhn.3.16' order by m.sort"""
print("\nJhn.3.16:")
hits = list(c.execute(q))
for a, scope, f_, t_, b in hits:
    print(f"  {a:<22} {scope:<8} v{f_}-{t_}  {b.strip()[:48]}...")
assert hits, "no commentary found for John 3:16 — the index is wrong"
