# -*- coding: utf-8 -*-
"""Cross-references: OpenBible.info's community-voted set, via scrollmapper.

Votes matter. The set is large enough that showing all of a verse's references
unranked is noise; the vote count is what lets a client show the strongest
first and hide the long tail behind "more".
"""
import glob, sqlite3, collections
DB="/home/claude/bible/build/bible.db"
SRC="/home/claude/bible/sources/xrefs"
NAMES={"Genesis":"Gen","Exodus":"Exo","Leviticus":"Lev","Numbers":"Num","Deuteronomy":"Deu",
"Joshua":"Jos","Judges":"Jdg","Ruth":"Rut","1 Samuel":"1Sa","2 Samuel":"2Sa","1 Kings":"1Ki",
"2 Kings":"2Ki","1 Chronicles":"1Ch","2 Chronicles":"2Ch","Ezra":"Ezr","Nehemiah":"Neh",
"Esther":"Est","Job":"Job","Psalms":"Psa","Psalm":"Psa","Proverbs":"Pro","Ecclesiastes":"Ecc",
"Song of Solomon":"Sng","Song of Songs":"Sng","Isaiah":"Isa","Jeremiah":"Jer",
"Lamentations":"Lam","Ezekiel":"Ezk","Daniel":"Dan","Hosea":"Hos","Joel":"Jol","Amos":"Amo",
"Obadiah":"Oba","Jonah":"Jon","Micah":"Mic","Nahum":"Nam","Habakkuk":"Hab","Zephaniah":"Zep",
"Haggai":"Hag","Zechariah":"Zec","Malachi":"Mal","Matthew":"Mat","Mark":"Mrk","Luke":"Luk",
"John":"Jhn","Acts":"Act","Romans":"Rom","1 Corinthians":"1Co","2 Corinthians":"2Co",
"Galatians":"Gal","Ephesians":"Eph","Philippians":"Php","Colossians":"Col",
"1 Thessalonians":"1Th","2 Thessalonians":"2Th","1 Timothy":"1Ti","2 Timothy":"2Ti",
"Titus":"Tit","Philemon":"Phm","Hebrews":"Heb","James":"Jas","1 Peter":"1Pe","2 Peter":"2Pe",
"1 John":"1Jn","2 John":"2Jn","3 John":"3Jn","Jude":"Jud","Revelation":"Rev",
"Revelation of John":"Rev","I Chronicles":"1Ch","II Chronicles":"2Ch","I Corinthians":"1Co",
"II Corinthians":"2Co","I John":"1Jn","II John":"2Jn","III John":"3Jn","I Kings":"1Ki",
"II Kings":"2Ki","I Peter":"1Pe","II Peter":"2Pe","I Samuel":"1Sa","II Samuel":"2Sa",
"I Thessalonians":"1Th","II Thessalonians":"2Th","I Timothy":"1Ti","II Timothy":"2Ti"}

db=sqlite3.connect(DB)
db.executescript("""
DROP TABLE IF EXISTS xref;
CREATE TABLE xref(
  from_key   TEXT NOT NULL,
  to_key     TEXT NOT NULL,   -- first verse of the target range
  to_end_key TEXT,            -- last verse when the target spans several
  votes      INT,             -- community confidence; higher is stronger
  PRIMARY KEY(from_key, to_key, to_end_key));
""")

rows=[]; unmapped=collections.Counter(); seen=set()
for path in sorted(glob.glob(SRC+"/xr_*.db")):
    src=sqlite3.connect(path)
    for fb, fc, fv, tb, tc, tvs, tve, votes in src.execute(
        "SELECT from_book, from_chapter, from_verse, to_book, to_chapter, "
        "to_verse_start, to_verse_end, votes FROM cross_references"):
        a=NAMES.get((fb or "").strip()); b=NAMES.get((tb or "").strip())
        if not a: unmapped[fb]+=1; continue
        if not b: unmapped[tb]+=1; continue
        frm=f"{a}.{fc}.{fv}"
        to=f"{b}.{tc}.{tvs}"
        end=f"{b}.{tc}.{tve}" if tve and tve!=tvs else None
        k=(frm,to,end)
        if k in seen: continue
        seen.add(k); rows.append((frm,to,end,votes))
    src.close()

db.executemany("INSERT OR IGNORE INTO xref VALUES (?,?,?,?)", rows)
db.executescript("""
CREATE INDEX IF NOT EXISTS ix_xref_from ON xref(from_key, votes DESC);
CREATE INDEX IF NOT EXISTS ix_xref_to   ON xref(to_key);
""")
db.commit()
n=lambda q: db.execute(q).fetchone()[0]
print(f"cross-references: {n('SELECT COUNT(*) FROM xref'):,}")
if unmapped: print("unmapped book names:", unmapped.most_common(5))
tot=n("SELECT COUNT(*) FROM xref")
okf=n("SELECT COUNT(*) FROM xref x WHERE EXISTS(SELECT 1 FROM verse v WHERE v.verse_key=x.from_key)")
okt=n("SELECT COUNT(*) FROM xref x WHERE EXISTS(SELECT 1 FROM verse v WHERE v.verse_key=x.to_key)")
print(f"  source verse resolves: {okf:,}/{tot:,} ({100*okf/tot:.2f}%)")
print(f"  target verse resolves: {okt:,}/{tot:,} ({100*okt/tot:.2f}%)")
print(f"  verses with at least one reference: {n('SELECT COUNT(DISTINCT from_key) FROM xref'):,}")
print("\nstrongest references from John 3:16:")
for r in db.execute("""SELECT to_key, to_end_key, votes FROM xref
                       WHERE from_key='Jhn.3.16' ORDER BY votes DESC LIMIT 5"""):
    print(f"   {r[0]}{'-'+r[1].split('.')[-1] if r[1] else '':6s}  votes {r[2]}")
db.close()
