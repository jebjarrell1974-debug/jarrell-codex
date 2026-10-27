"""Ingest Theographic: people, events timeline, Easton's dictionary, and their verse links."""
import json, re, sqlite3, os
DB="/home/claude/bible/build/bible.db"
J="/home/claude/bible/sources/theographic-bible-metadata/json"
# OSIS book abbreviations -> our canonical codes
OSIS={"Gen":"Gen","Exod":"Exo","Lev":"Lev","Num":"Num","Deut":"Deu","Josh":"Jos","Judg":"Jdg",
"Ruth":"Rut","1Sam":"1Sa","2Sam":"2Sa","1Kgs":"1Ki","2Kgs":"2Ki","1Chr":"1Ch","2Chr":"2Ch",
"Ezra":"Ezr","Neh":"Neh","Esth":"Est","Job":"Job","Ps":"Psa","Prov":"Pro","Eccl":"Ecc",
"Song":"Sng","Isa":"Isa","Jer":"Jer","Lam":"Lam","Ezek":"Ezk","Dan":"Dan","Hos":"Hos",
"Joel":"Jol","Amos":"Amo","Obad":"Oba","Jonah":"Jon","Mic":"Mic","Nah":"Nam","Hab":"Hab",
"Zeph":"Zep","Hag":"Hag","Zech":"Zec","Mal":"Mal","Matt":"Mat","Mark":"Mrk","Luke":"Luk",
"John":"Jhn","Acts":"Act","Rom":"Rom","1Cor":"1Co","2Cor":"2Co","Gal":"Gal","Eph":"Eph",
"Phil":"Php","Col":"Col","1Thess":"1Th","2Thess":"2Th","1Tim":"1Ti","2Tim":"2Ti","Titus":"Tit",
"Phlm":"Phm","Heb":"Heb","Jas":"Jas","1Pet":"1Pe","2Pet":"2Pe","1John":"1Jn","2John":"2Jn",
"3John":"3Jn","Jude":"Jud","Rev":"Rev"}
load=lambda n: json.load(open(f"{J}/{n}",encoding="utf-8"))
F=lambda r: r.get("fields",{})

def vkey(osis):
    if not osis: return None
    m=re.match(r'^([1-3]?[A-Za-z]+)\.(\d+)\.(\d+)$', osis.strip())
    if not m: return None
    bk=OSIS.get(m.group(1))
    return f"{bk}.{m.group(2)}.{m.group(3)}" if bk else None

verses=load("verses.json")
vmap={}   # airtable rec id -> canonical verse key
unmapped=set()
for r in verses:
    k=vkey(F(r).get("osisRef"))
    if k: vmap[r["id"]]=k
    else: unmapped.add(F(r).get("osisRef"))

people=load("people.json"); events=load("events.json"); easton=load("easton.json")
pmap={r["id"]: F(r).get("personID") for r in people}

db=sqlite3.connect(DB)
db.executescript("""
DROP TABLE IF EXISTS person; DROP TABLE IF EXISTS person_verse;
DROP TABLE IF EXISTS event;  DROP TABLE IF EXISTS event_verse;
DROP TABLE IF EXISTS dictionary;
CREATE TABLE person(
  person_id INT PRIMARY KEY, name TEXT, display_title TEXT, slug TEXT,
  gender TEXT, is_proper_name INT, birth_year INT, death_year INT, dictionary_url TEXT);
CREATE TABLE person_verse(person_id INT, verse_key TEXT, PRIMARY KEY(person_id, verse_key));
CREATE TABLE event(
  event_id INT PRIMARY KEY, title TEXT, start_date INT, duration TEXT,
  sort_key REAL, verse_sort TEXT);
CREATE TABLE event_verse(event_id INT, verse_key TEXT, PRIMARY KEY(event_id, verse_key));
-- One termID covers a headword with several numbered senses (Abda, Abda 1,
-- Abda 2), so the key is the record id, not the termID.
CREATE TABLE dictionary(
  entry_id TEXT PRIMARY KEY, term_id TEXT, term_label TEXT, lookup TEXT,
  item_num INT, body TEXT, match_type TEXT, person_slug TEXT, source TEXT);
""")

db.executemany("INSERT OR REPLACE INTO person VALUES (?,?,?,?,?,?,?,?,?)",
  [(F(r).get("personID"), F(r).get("name"), F(r).get("displayTitle"), F(r).get("slug"),
    F(r).get("gender"), 1 if F(r).get("isProperName") else 0,
    F(r).get("birthYear"), F(r).get("deathYear"), F(r).get("dictionaryLink"))
   for r in people if F(r).get("personID") is not None])

pv=set()
for r in verses:
    k=vmap.get(r["id"])
    if not k: continue
    for rid in F(r).get("people") or []:
        pid=pmap.get(rid)
        if pid is not None: pv.add((pid,k))
db.executemany("INSERT OR IGNORE INTO person_verse VALUES (?,?)", pv)

db.executemany("INSERT OR REPLACE INTO event VALUES (?,?,?,?,?,?)",
  [(F(r).get("eventID"), F(r).get("title"), F(r).get("startDate"), F(r).get("duration"),
    F(r).get("sortKey"), F(r).get("verseSort")) for r in events if F(r).get("eventID") is not None])
ev=set()
for r in events:
    eid=F(r).get("eventID")
    if eid is None: continue
    for rid in F(r).get("verses") or []:
        k=vmap.get(rid)
        if k: ev.add((eid,k))
db.executemany("INSERT OR IGNORE INTO event_verse VALUES (?,?)", ev)

def _slug(r):
    m=F(r).get("matchSlugs")
    if not m or m=="unmatched": return None
    return m[0] if isinstance(m,list) else str(m)
db.executemany("INSERT OR REPLACE INTO dictionary VALUES (?,?,?,?,?,?,?,?,?)",
  [(r["id"], F(r).get("termID"), F(r).get("termLabel"), F(r).get("dictLookup"),
    int(F(r).get("itemNum") or 0), (F(r).get("dictText") or "").strip(),
    F(r).get("matchType"), _slug(r), "Easton's Bible Dictionary (1897)")
   for r in easton])

db.executescript("""
CREATE INDEX IF NOT EXISTS ix_pv_v ON person_verse(verse_key);
CREATE INDEX IF NOT EXISTS ix_ev_v ON event_verse(verse_key);
CREATE INDEX IF NOT EXISTS ix_ev_sort ON event(sort_key);
CREATE INDEX IF NOT EXISTS ix_dict_label ON dictionary(term_label);
CREATE INDEX IF NOT EXISTS ix_dict_term  ON dictionary(term_id);
CREATE INDEX IF NOT EXISTS ix_dict_slug  ON dictionary(person_slug);
CREATE INDEX IF NOT EXISTS ix_person_name ON person(name);
""")
db.commit()
c=lambda t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
print(f"people {c('person'):,}   person-verse {c('person_verse'):,}")
print(f"events {c('event'):,}    event-verse {c('event_verse'):,}")
heads=db.execute("SELECT COUNT(DISTINCT term_id) FROM dictionary").fetchone()[0]
linked=db.execute("SELECT COUNT(*) FROM dictionary WHERE person_slug IS NOT NULL").fetchone()[0]
print(f"dictionary {c('dictionary'):,} senses across {heads:,} headwords; {linked:,} linked to a person")
print(f"verse rec ids mapped: {len(vmap):,}/{len(verses):,}")
if unmapped: print("unmapped osis books:", sorted({u.split('.')[0] for u in unmapped if u})[:10])
tot=c('person_verse'); ok=db.execute("SELECT COUNT(*) FROM person_verse pv WHERE EXISTS(SELECT 1 FROM verse v WHERE v.verse_key=pv.verse_key)").fetchone()[0]
print(f"person-verse links resolving to a canonical verse: {ok:,}/{tot:,} ({100*ok/tot:.2f}%)")
tot=c('event_verse'); ok=db.execute("SELECT COUNT(*) FROM event_verse ev WHERE EXISTS(SELECT 1 FROM verse v WHERE v.verse_key=ev.verse_key)").fetchone()[0]
print(f"event-verse links resolving:  {ok:,}/{tot:,} ({100*ok/tot:.2f}%)")
db.close()
