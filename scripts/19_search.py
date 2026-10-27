# -*- coding: utf-8 -*-
"""Full-text search, plus reference parsing.

FTS4, not FTS5, on purpose. Android only enables FTS5 from Android 10, and this
app is meant to run on handed-down phones. FTS4 is available on every Android
version this app supports. The corpus is small enough that the performance
difference does not matter, and results are ordered by canonical book order
rather than relevance - which is what a reader expects anyway: Genesis before
Revelation, not whichever verse happened to score highest.
"""
import re, sqlite3, time, unicodedata
DB="/home/claude/bible/build/bible.db"
db=sqlite3.connect(DB)

db.executescript("""
DROP TABLE IF EXISTS search_verse;
DROP TABLE IF EXISTS search_note;
DROP TABLE IF EXISTS search_lexicon;
DROP TABLE IF EXISTS book_name;

-- English text of every translation, one row per verse per translation.
CREATE VIRTUAL TABLE search_verse USING fts4(
  verse_key, code, text, tokenize=unicode61);

-- The context notes.
CREATE VIRTUAL TABLE search_note USING fts4(
  note_id, verse_key, body, tokenize=unicode61);

-- Lexicon entries, searchable by gloss or English definition, so a reader can
-- look for a concept and arrive at the Hebrew or Greek word behind it.
CREATE VIRTUAL TABLE search_lexicon USING fts4(
  strongs, lemma, gloss, definition, tokenize=unicode61);

-- Book names and abbreviations, for parsing a typed reference.
CREATE TABLE book_name(
  name TEXT PRIMARY KEY COLLATE NOCASE, book TEXT NOT NULL, kind TEXT);
""")

db.execute("INSERT INTO search_verse(verse_key, code, text) "
           "SELECT canonical_key, code, text FROM translation_verse WHERE canonical_key IS NOT NULL")
db.execute("INSERT INTO search_note(note_id, verse_key, body) "
           "SELECT note_id, verse_key, body FROM note")
db.execute("INSERT INTO search_lexicon(strongs, lemma, gloss, definition) "
           "SELECT strongs, lemma, gloss, definition FROM lexicon")

FULL={"Gen":["Genesis"],"Exo":["Exodus"],"Lev":["Leviticus"],"Num":["Numbers"],
"Deu":["Deuteronomy"],"Jos":["Joshua"],"Jdg":["Judges"],"Rut":["Ruth"],
"1Sa":["1 Samuel","First Samuel","I Samuel"],"2Sa":["2 Samuel","Second Samuel","II Samuel"],
"1Ki":["1 Kings","First Kings","I Kings"],"2Ki":["2 Kings","Second Kings","II Kings"],
"1Ch":["1 Chronicles","I Chronicles"],"2Ch":["2 Chronicles","II Chronicles"],
"Ezr":["Ezra"],"Neh":["Nehemiah"],"Est":["Esther"],"Job":["Job"],
"Psa":["Psalms","Psalm"],"Pro":["Proverbs"],"Ecc":["Ecclesiastes"],
"Sng":["Song of Solomon","Song of Songs","Canticles"],"Isa":["Isaiah"],"Jer":["Jeremiah"],
"Lam":["Lamentations"],"Ezk":["Ezekiel"],"Dan":["Daniel"],"Hos":["Hosea"],"Jol":["Joel"],
"Amo":["Amos"],"Oba":["Obadiah"],"Jon":["Jonah"],"Mic":["Micah"],"Nam":["Nahum"],
"Hab":["Habakkuk"],"Zep":["Zephaniah"],"Hag":["Haggai"],"Zec":["Zechariah"],"Mal":["Malachi"],
"Mat":["Matthew"],"Mrk":["Mark"],"Luk":["Luke"],"Jhn":["John"],"Act":["Acts","Acts of the Apostles"],
"Rom":["Romans"],"1Co":["1 Corinthians","I Corinthians"],"2Co":["2 Corinthians","II Corinthians"],
"Gal":["Galatians"],"Eph":["Ephesians"],"Php":["Philippians"],"Col":["Colossians"],
"1Th":["1 Thessalonians","I Thessalonians"],"2Th":["2 Thessalonians","II Thessalonians"],
"1Ti":["1 Timothy","I Timothy"],"2Ti":["2 Timothy","II Timothy"],"Tit":["Titus"],
"Phm":["Philemon"],"Heb":["Hebrews"],"Jas":["James"],"1Pe":["1 Peter","I Peter"],
"2Pe":["2 Peter","II Peter"],"1Jn":["1 John","I John"],"2Jn":["2 John","II John"],
"3Jn":["3 John","III John"],"Jud":["Jude"],"Rev":["Revelation","Revelation of John","Apocalypse"]}
COMMON={"Gen":["Gn"],"Exo":["Ex"],"Lev":["Lv"],"Num":["Nm","Nu"],"Deu":["Dt","Deut"],
"Jos":["Josh"],"Jdg":["Judg"],"1Sa":["1Sam","1 Sam"],"2Sa":["2Sam","2 Sam"],
"1Ki":["1Kgs","1 Kgs"],"2Ki":["2Kgs","2 Kgs"],"1Ch":["1Chr","1 Chr"],"2Ch":["2Chr","2 Chr"],
"Psa":["Ps","Pss"],"Pro":["Prov","Prv"],"Ecc":["Eccl","Qoh"],"Sng":["Song","SoS"],
"Isa":["Is"],"Jer":["Jr"],"Ezk":["Ezek","Eze"],"Mat":["Matt","Mt"],"Mrk":["Mk","Mar"],
"Luk":["Lk","Lu"],"Jhn":["Jn","Joh"],"Rom":["Rm"],"1Co":["1Cor","1 Cor"],"2Co":["2Cor","2 Cor"],
"Php":["Phil","Phi"],"Col":["Cl"],"1Th":["1Thess","1 Thess"],"2Th":["2Thess","2 Thess"],
"1Ti":["1Tim","1 Tim"],"2Ti":["2Tim","2 Tim"],"Phm":["Phlm","Philem"],"Heb":["Hb"],
"Jas":["Jam","Jms"],"1Pe":["1Pet","1 Pet"],"2Pe":["2Pet","2 Pet"],
"1Jn":["1John","1 John"],"2Jn":["2John","2 John"],"3Jn":["3John","3 John"],"Rev":["Rv","Apoc"]}

rows=[]
for bk in FULL:
    rows.append((bk, bk, "code"))
    for n in FULL[bk]: rows.append((n, bk, "full"))
    for n in COMMON.get(bk, []): rows.append((n, bk, "abbrev"))
seen=set(); uniq=[]
for n,b,k in rows:
    key=n.lower()
    if key in seen: continue
    seen.add(key); uniq.append((n,b,k))
db.executemany("INSERT OR IGNORE INTO book_name VALUES (?,?,?)", uniq)
db.commit()

n=lambda t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
print(f"search_verse   {n('search_verse'):,} rows")
print(f"search_note    {n('search_note'):,} rows")
print(f"search_lexicon {n('search_lexicon'):,} rows")
print(f"book_name      {n('book_name'):,} names and abbreviations")

def timed(label, q, *p):
    t=time.perf_counter(); r=db.execute(q,p).fetchall(); ms=(time.perf_counter()-t)*1000
    print(f"  {label:50s} {ms:7.1f} ms  {len(r):>5} rows")
    return r, ms

print("\n=== search timings")
slow=[]
_,m1=timed("phrase in every translation: 'good shepherd'",
  """SELECT v.verse_key, v.code FROM search_verse v WHERE search_verse MATCH ? LIMIT 100""",
  '"good shepherd"'); slow.append(m1)
_,m2=timed("common word: 'love'",
  """SELECT verse_key, code FROM search_verse WHERE search_verse MATCH 'love' LIMIT 100""")
slow.append(m2)
_,m3=timed("notes: 'covenant'",
  """SELECT note_id FROM search_note WHERE search_note MATCH 'covenant' LIMIT 100""")
slow.append(m3)
_,m4=timed("lexicon by meaning: 'steadfast love'",
  """SELECT strongs, lemma, gloss FROM search_lexicon WHERE search_lexicon MATCH ? LIMIT 50""",
  '"steadfast love"'); slow.append(m4)
_,m5=timed("two words: 'faith works'",
  """SELECT verse_key FROM search_verse WHERE search_verse MATCH 'faith works' LIMIT 100""")
slow.append(m5)
print(f"\n  slowest {max(slow):.1f} ms   {'PASS' if max(slow)<400 else 'FAIL'}: search under 400 ms")
db.close()
