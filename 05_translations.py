"""Load public-domain English translations onto the canonical verse key."""
import json, sqlite3, glob, os, re
DB="/home/claude/bible/build/bible.db"
TR="/home/claude/bible/sources/translations"
NAMES={"Genesis":"Gen","Exodus":"Exo","Leviticus":"Lev","Numbers":"Num","Deuteronomy":"Deu",
"Joshua":"Jos","Judges":"Jdg","Ruth":"Rut","1 Samuel":"1Sa","2 Samuel":"2Sa","1 Kings":"1Ki",
"2 Kings":"2Ki","1 Chronicles":"1Ch","2 Chronicles":"2Ch","Ezra":"Ezr","Nehemiah":"Neh",
"Esther":"Est","Job":"Job","Psalms":"Psa","Proverbs":"Pro","Ecclesiastes":"Ecc",
"Song of Solomon":"Sng","Isaiah":"Isa","Jeremiah":"Jer","Lamentations":"Lam","Ezekiel":"Ezk",
"Daniel":"Dan","Hosea":"Hos","Joel":"Jol","Amos":"Amo","Obadiah":"Oba","Jonah":"Jon",
"Micah":"Mic","Nahum":"Nam","Habakkuk":"Hab","Zephaniah":"Zep","Haggai":"Hag",
"Zechariah":"Zec","Malachi":"Mal","Matthew":"Mat","Mark":"Mrk","Luke":"Luk","John":"Jhn",
"Acts":"Act","Romans":"Rom","1 Corinthians":"1Co","2 Corinthians":"2Co","Galatians":"Gal",
"Ephesians":"Eph","Philippians":"Php","Colossians":"Col","1 Thessalonians":"1Th",
"2 Thessalonians":"2Th","1 Timothy":"1Ti","2 Timothy":"2Ti","Titus":"Tit","Philemon":"Phm",
"Hebrews":"Heb","James":"Jas","1 Peter":"1Pe","2 Peter":"2Pe","1 John":"1Jn","2 John":"2Jn",
"3 John":"3Jn","Jude":"Jud","Revelation":"Rev"}
# Some editions spell the numbered books with Roman numerals and name Revelation
# differently; alias them rather than silently dropping 18 books.
for _roman, _ar in (("I ","1 "),("II ","2 "),("III ","3 ")):
    for _full, _ab in list(NAMES.items()):
        if _full.startswith(_ar):
            NAMES[_roman + _full[len(_ar):]] = _ab
NAMES["Revelation of John"]="Rev"
NAMES["The Revelation"]="Rev"
NAMES["Song of Songs"]="Sng"
NAMES["Psalm"]="Psa"
db=sqlite3.connect(DB)
db.executescript("""
DROP TABLE IF EXISTS translation; DROP TABLE IF EXISTS translation_verse;
CREATE TABLE translation(code TEXT PRIMARY KEY, name TEXT, licence TEXT);
CREATE TABLE translation_verse(
  code TEXT, verse_key TEXT, chapter INT, verse INT, text TEXT,
  PRIMARY KEY(code, verse_key));
""")
META={"KJV":("King James Version (1769)","Public domain"),
      "ASV":("American Standard Version (1901)","Public domain"),
      "YLT":("Young's Literal Translation (1862/1898)","Public domain"),
      "Darby":("Darby Translation (1890)","Public domain")}
unknown=set()
for path in sorted(glob.glob(TR+"/*.json")):
    code=os.path.splitext(os.path.basename(path))[0]
    d=json.load(open(path,encoding="utf-8"))
    name,lic=META.get(code,(d.get("translation",code),"Public domain"))
    db.execute("INSERT OR REPLACE INTO translation VALUES (?,?,?)",(code,name,lic))
    rows=[]
    for b in d["books"]:
        abbr=NAMES.get(b["name"].strip())
        if not abbr: unknown.add(b["name"]); continue
        for ch in b["chapters"]:
            cn=ch.get("chapter") or ch.get("number")
            for v in ch["verses"]:
                vn=v.get("verse") or v.get("number")
                rows.append((code,f"{abbr}.{cn}.{vn}",cn,vn,v["text"].strip()))
    db.executemany("INSERT OR REPLACE INTO translation_verse VALUES (?,?,?,?,?)",rows)
    print(f"  {code:6s} {len(rows):6,} verses  ({name})")
db.commit()
if unknown: print("UNMAPPED BOOK NAMES:", sorted(unknown))
tot=db.execute("SELECT COUNT(*) FROM translation_verse").fetchone()[0]
matched=db.execute("""SELECT COUNT(*) FROM translation_verse tv
                      WHERE EXISTS(SELECT 1 FROM verse v WHERE v.verse_key=tv.verse_key)""").fetchone()[0]
print(f"\ntranslation verses: {tot:,}   aligned to a canonical verse: {matched:,} ({100*matched/tot:.1f}%)")
db.close()
