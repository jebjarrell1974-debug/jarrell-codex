# -*- coding: utf-8 -*-
"""Ingest unfoldingWord translationNotes - the cultural/historical context layer.

CC BY-SA 4.0. Obligations carried in ATTRIBUTION.md: attribute to
unfoldingword.org/utn, state what was changed, licence derivatives alike, and
remove the unfoldingWord trademark from derivative work.
"""
import csv, glob, os, re, sqlite3
DB="/home/claude/bible/build/bible.db"
SRC="/home/claude/bible/sources/uw_tn"
USFM={"GEN":"Gen","EXO":"Exo","LEV":"Lev","NUM":"Num","DEU":"Deu","JOS":"Jos","JDG":"Jdg",
"RUT":"Rut","1SA":"1Sa","2SA":"2Sa","1KI":"1Ki","2KI":"2Ki","1CH":"1Ch","2CH":"2Ch","EZR":"Ezr",
"NEH":"Neh","EST":"Est","JOB":"Job","PSA":"Psa","PRO":"Pro","ECC":"Ecc","SNG":"Sng","ISA":"Isa",
"JER":"Jer","LAM":"Lam","EZK":"Ezk","DAN":"Dan","HOS":"Hos","JOL":"Jol","AMO":"Amo","OBA":"Oba",
"JON":"Jon","MIC":"Mic","NAM":"Nam","HAB":"Hab","ZEP":"Zep","HAG":"Hag","ZEC":"Zec","MAL":"Mal",
"MAT":"Mat","MRK":"Mrk","LUK":"Luk","JHN":"Jhn","ACT":"Act","ROM":"Rom","1CO":"1Co","2CO":"2Co",
"GAL":"Gal","EPH":"Eph","PHP":"Php","COL":"Col","1TH":"1Th","2TH":"2Th","1TI":"1Ti","2TI":"2Ti",
"TIT":"Tit","PHM":"Phm","HEB":"Heb","JAS":"Jas","1PE":"1Pe","2PE":"2Pe","1JN":"1Jn","2JN":"2Jn",
"3JN":"3Jn","JUD":"Jud","REV":"Rev"}

def clean(s):
    if not s: return ""
    s=s.replace("\\n","\n")
    # "(See: rc://...; and rc://...)" trailers are navigation into unfoldingWord's
    # own site. They point at pages this app does not ship, so they are debris
    # here rather than help. Drop the whole parenthetical.
    s=re.sub(r'\(\s*See:\s*[^)]*rc://[^)]*\)', '', s, flags=re.I)
    # Any rc:// link left standing: keep the readable last segment.
    s=re.sub(r'rc://\S*?/([a-z0-9-]+)(?=[\s;,.)\]]|$)', r'\1', s)
    s=re.sub(r'rc://\S+', '', s)
    s=re.sub(r'\[\[([^\]]+)\]\]', r'\1', s)
    s=re.sub(r'[ \t]{2,}', ' ', s)
    return s.strip()

db=sqlite3.connect(DB)
db.executescript("""
DROP TABLE IF EXISTS note;
CREATE TABLE note(
  note_id   TEXT PRIMARY KEY,   -- book + reference + source id
  verse_key TEXT,               -- NULL for book/chapter introductions
  book      TEXT NOT NULL,
  chapter   INT,                -- NULL for the book introduction
  verse     INT,                -- NULL for an introduction
  kind      TEXT NOT NULL,      -- verse | chapter_intro | book_intro
  quote     TEXT,               -- the original-language words the note is about
  occurrence INT,
  category  TEXT,               -- translate helper, e.g. figs-abstractnouns
  body      TEXT NOT NULL,
  source    TEXT NOT NULL);
""")

rows=[]; skipped=0; books=0
for path in sorted(glob.glob(SRC+"/tn_*.tsv")):
    code=os.path.basename(path)[3:-4].upper()
    bk=USFM.get(code)
    if not bk: skipped+=1; continue
    books+=1
    with open(path, encoding="utf-8", newline="") as fh:
        rd=csv.DictReader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
        for r in rd:
            ref=(r.get("Reference") or "").strip()
            body=clean(r.get("Note"))
            if not ref or not body: continue
            nid=f"{bk}:{ref}:{(r.get('ID') or '').strip()}"
            ch=vs=None; kind="verse"; vk=None
            if ref.startswith("front:"):
                kind="book_intro"
            else:
                m=re.match(r'^(\d+):(\d+)$', ref)
                if m:
                    ch, vs = int(m.group(1)), int(m.group(2))
                    vk=f"{bk}.{ch}.{vs}"
                else:
                    m=re.match(r'^(\d+):intro$', ref)
                    if m: ch=int(m.group(1)); kind="chapter_intro"
                    else: continue
            cat=(r.get("SupportReference") or "").strip()
            cat=re.sub(r'^rc://\*/ta/man/translate/','',cat) or None
            occ=(r.get("Occurrence") or "").strip()
            rows.append((nid, vk, bk, ch, vs, kind,
                         (r.get("Quote") or "").strip() or None,
                         int(occ) if occ.lstrip("-").isdigit() else None,
                         cat, body, "unfoldingWord translationNotes (CC BY-SA 4.0)"))

db.executemany("INSERT OR REPLACE INTO note VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
db.executescript("""
CREATE INDEX IF NOT EXISTS ix_note_verse ON note(verse_key);
CREATE INDEX IF NOT EXISTS ix_note_book  ON note(book, chapter, verse);
CREATE INDEX IF NOT EXISTS ix_note_cat   ON note(category);
""")
db.commit()
c=lambda q,*p: db.execute(q,p).fetchone()[0]
print(f"books ingested: {books}  (skipped {skipped})")
print(f"notes: {c('SELECT COUNT(*) FROM note'):,}")
for k,n in db.execute("SELECT kind, COUNT(*) FROM note GROUP BY 1 ORDER BY 2 DESC"):
    print(f"  {k:14s} {n:,}")
tot=c("SELECT COUNT(*) FROM note WHERE verse_key IS NOT NULL")
ok=c("""SELECT COUNT(*) FROM note n WHERE n.verse_key IS NOT NULL
        AND EXISTS(SELECT 1 FROM verse v WHERE v.verse_key=n.verse_key)""")
print(f"verse notes resolving to a canonical verse: {ok:,}/{tot:,} ({100*ok/tot:.2f}%)")
print(f"notes carrying an original-language quote: {c('SELECT COUNT(*) FROM note WHERE quote IS NOT NULL'):,}")
print(f"distinct translate categories: {c('SELECT COUNT(DISTINCT category) FROM note WHERE category IS NOT NULL'):,}")
db.close()
