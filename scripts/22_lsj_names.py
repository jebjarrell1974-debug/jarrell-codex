# -*- coding: utf-8 -*-
"""Full LSJ lexicon + disambiguated proper names, both from STEPBible."""
import re, html, sqlite3, glob
DB="/home/claude/bible/build/bible.db"
LEX="/home/claude/bible/sources/stepbible/Lexicons"
PN=glob.glob("/home/claude/bible/sources/stepbible/Proper Nouns/TIPNR*.txt")[0]
db=sqlite3.connect(DB)

# ---------------------------------------------------------------- full LSJ
def strip_html(s):
    s=re.sub(r'<a\b[^>]*>(.*?)</a>', r'\1', s, flags=re.S|re.I)
    s=re.sub(r'<br\s*/?>', ' | ', s, flags=re.I)
    s=re.sub(r'<[^>]+>', '', s)
    s=html.unescape(s)
    return re.sub(r'\s{2,}', ' ', s).strip()

db.executescript("""
DROP TABLE IF EXISTS lexicon_full;
CREATE TABLE lexicon_full(
  strongs TEXT PRIMARY KEY, estrong TEXT, lemma TEXT, translit TEXT,
  gloss TEXT, entry TEXT, source TEXT);
""")
ROW=re.compile(r'^([HG]\d{4}[A-Za-z]?)\t')
rows={}
for path in glob.glob(LEX+"/TFLSJ*.txt"):
    for line in open(path, encoding="utf-8-sig"):
        if not ROW.match(line): continue
        c=line.rstrip("\n").split("\t")
        if len(c)<8: continue
        d=c[1].split("=")[0].strip() or c[0].strip()
        if d in rows: continue
        rows[d]=(d, c[0].strip(), c[3].strip(), c[4].strip(), c[6].strip(),
                 strip_html(c[7])[:20000],
                 "Liddell-Scott-Jones, formatted by STEPBible (CC BY 4.0)")
db.executemany("INSERT OR REPLACE INTO lexicon_full VALUES (?,?,?,?,?,?,?)", rows.values())

# ------------------------------------------------------- proper names
db.executescript("""
DROP TABLE IF EXISTS proper_name;
DROP TABLE IF EXISTS proper_name_ref;
CREATE TABLE proper_name(
  unified   TEXT PRIMARY KEY,   -- e.g. Aaron@Exo.4.14-Heb : name + first occurrence
  name      TEXT,
  strongs   TEXT,
  description TEXT,
  parents   TEXT, siblings TEXT, spouse TEXT, children TEXT, affiliation TEXT);
CREATE TABLE proper_name_ref(
  unified   TEXT NOT NULL,
  verse_key TEXT NOT NULL,
  form      TEXT,              -- Named | Greek | Spelled | Aramaic ...
  native    TEXT,              -- the Hebrew or Greek word
  PRIMARY KEY(unified, verse_key, form));
""")

BOOK=re.compile(r'^([1-5A-Za-z]{2,3})\.(\d+)\.(\d+)[a-z]?$')
VALID={r[0] for r in db.execute("SELECT DISTINCT book FROM verse")}
people={}; refs=set(); cur=None
for line in open(PN, encoding="utf-8-sig"):
    c=line.rstrip("\n").split("\t")
    if not c or not c[0]: continue
    head=c[0].strip()
    m=re.match(r'^([A-Za-z][^\t@]*@[^\s=]+)=([HG]\d{4}[A-Za-z]?)$', head)
    if m and len(c)>=2:
        cur=m.group(1)
        people[cur]=(cur, cur.split("@")[0], m.group(2),
                     (c[1] if len(c)>1 else "").strip() or None,
                     (c[2] if len(c)>2 else "").strip() or None,
                     (c[3] if len(c)>3 else "").strip() or None,
                     (c[4] if len(c)>4 else "").strip() or None,
                     (c[5] if len(c)>5 else "").strip() or None,
                     (c[6] if len(c)>6 else "").strip() or None)
        continue
    if head.startswith("–") and len(c) >= 5:
        form=head.lstrip("– ").strip()
        unified=(c[1] or "").strip() or cur
        if not unified: continue
        native=None
        mm=re.search(r'=(.+)$', (c[2] or "").strip())
        if mm: native=mm.group(1).strip()
        for ref in re.split(r'[;,]', c[4] or ""):
            ref=ref.strip()
            if not ref: continue
            b=BOOK.match(ref)
            if not b: continue
            if b.group(1) not in VALID: continue
            refs.add((unified, f"{b.group(1)}.{b.group(2)}.{b.group(3)}", form, native))

db.executemany("INSERT OR REPLACE INTO proper_name VALUES (?,?,?,?,?,?,?,?,?)", people.values())
db.executemany("INSERT OR IGNORE INTO proper_name_ref VALUES (?,?,?,?)", refs)
db.executescript("""
CREATE INDEX IF NOT EXISTS ix_pnr_verse ON proper_name_ref(verse_key);
CREATE INDEX IF NOT EXISTS ix_pnr_uni   ON proper_name_ref(unified);
CREATE INDEX IF NOT EXISTS ix_pn_name   ON proper_name(name);
CREATE INDEX IF NOT EXISTS ix_lexfull_e ON lexicon_full(estrong);
""")
db.commit()
n=lambda q: db.execute(q).fetchone()[0]
print(f"full LSJ entries: {n('SELECT COUNT(*) FROM lexicon_full'):,}")
print(f"  avg entry length: {n('SELECT CAST(AVG(length(entry)) AS INT) FROM lexicon_full'):,} chars "
      f"(brief lexicon: {n('SELECT CAST(AVG(length(definition)) AS INT) FROM lexicon'):,})")
print(f"proper names: {n('SELECT COUNT(*) FROM proper_name'):,}")
print(f"name references: {n('SELECT COUNT(*) FROM proper_name_ref'):,}")
bad=n("""SELECT COUNT(*) FROM proper_name_ref r
         WHERE NOT EXISTS(SELECT 1 FROM verse v WHERE v.verse_key=r.verse_key)""")
print(f"  references resolving to a canonical verse: "
      f"{n('SELECT COUNT(*) FROM proper_name_ref')-bad:,}/{n('SELECT COUNT(*) FROM proper_name_ref'):,}")
print("\nthe different Marys:")
for r in db.execute("""SELECT unified, description FROM proper_name
                       WHERE name='Mary' ORDER BY unified"""):
    print(f"   {r[0]:34s} {(r[1] or '')[:62]}")
db.close()
