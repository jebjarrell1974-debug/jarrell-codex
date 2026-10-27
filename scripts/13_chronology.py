# -*- coding: utf-8 -*-
"""Chronology as a selectable scheme, not a silent assertion.

The event timeline inherited from Theographic carries ONE set of dates. Shipping
those unlabelled would have the app assert a contested chronology as fact. This
turns dates into per-scheme data with provenance, and makes "this scheme has no
date for that event" a first-class answer rather than a silent fallback.
"""
import sqlite3
DB="/home/claude/bible/build/bible.db"
db=sqlite3.connect(DB)

db.executescript("""
DROP TABLE IF EXISTS chronology_scheme;
DROP TABLE IF EXISTS event_date;
DROP TABLE IF EXISTS chronology_note;

CREATE TABLE chronology_scheme(
  scheme_id     TEXT PRIMARY KEY,
  name          TEXT NOT NULL,
  tradition     TEXT,       -- which text or method it rests on
  creation_year INT,        -- its date for creation, where it offers one
  coverage      TEXT,       -- 'full' | 'anchors' | 'none'
  summary       TEXT,
  source        TEXT,
  is_default    INT DEFAULT 0,
  sort_order    INT);

CREATE TABLE event_date(
  event_id   INT  NOT NULL,
  scheme_id  TEXT NOT NULL,
  start_year INT,
  end_year   INT,
  precision  TEXT,          -- 'stated' | 'derived' | 'approximate'
  note       TEXT,
  PRIMARY KEY(event_id, scheme_id));

CREATE TABLE chronology_note(
  note_id   TEXT PRIMARY KEY,
  heading   TEXT,
  body      TEXT,
  sort_order INT);
""")

SCHEMES=[
 ("jones","Floyd Nolen Jones","Masoretic Text",-4003,"full",
  "A conservative Masoretic chronology that treats the Genesis 5 and 11 genealogies as "
  "continuous, with no gaps between father and son. It is the scheme the underlying event "
  "timeline was compiled under, so it is the only one here with a date for every event.",
  "Floyd Nolen Jones, The Chronology of the Old Testament, via Theographic Bible Metadata",1,1),
 ("ussher","James Ussher (1650)","Masoretic Text",-4004,"anchors",
  "The most famous biblical chronology, published in the Annals of the World and printed in "
  "the margins of many King James Bibles. Ussher placed the first day of creation on "
  "23 October 4004 BC. Like Jones he reads the genealogies as continuous; the two differ by "
  "only a year or two at most points.",
  "James Ussher, Annals of the World (1650, English 1658)",0,2),
 ("septuagint","Septuagint (LXX) reckoning","Greek Septuagint",None,"none",
  "The Greek Old Testament gives different ages in the patriarchal genealogies and inserts an "
  "extra ancestor after the flood, producing a far longer span - roughly 4,777 years from "
  "creation to the completion of the Second Temple. Early Christian writers such as Eusebius "
  "worked from these figures. No per-event dates are loaded for this scheme.",
  "Chronology of the Bible (overview of textual traditions)",0,3),
 ("samaritan","Samaritan Pentateuch reckoning","Samaritan Pentateuch",None,"none",
  "The Samaritan Pentateuch gives yet another set of genealogical figures, yielding roughly "
  "3,000 years from creation to the settlement of Canaan. It is the shortest of the three "
  "textual traditions. No per-event dates are loaded for this scheme.",
  "Chronology of the Bible (overview of textual traditions)",0,4),
 ("thiele","Edwin R. Thiele","Regnal records plus Assyrian synchronisms",None,"anchors",
  "Not a chronology of the whole Bible but of the Hebrew monarchy, and the usual starting "
  "point for scholarly work on it. Thiele worked inductively from how ancient scribes actually "
  "counted regnal years: Judah used accession-year reckoning and Israel non-accession, Israel's "
  "year began in spring and Judah's in autumn, and co-regencies overlap. That resolves most of "
  "the apparent contradictions in Kings. Later scholars corrected him on points such as "
  "Hezekiah's co-regency with Ahaz.",
  "Edwin R. Thiele, The Mysterious Numbers of the Hebrew Kings",0,5),
 ("critical","Mainstream critical","Archaeology and external records",None,"anchors",
  "Rather than counting genealogies, this approach anchors the biblical narrative to dates "
  "fixed by Assyrian, Babylonian and Egyptian records and by archaeology. It offers no date "
  "for creation at all, treats the primeval history as outside the reach of chronology, and "
  "becomes confident only from the divided monarchy onward.",
  "Standard reference works on ancient Near Eastern chronology",0,6),
]
db.executemany("INSERT INTO chronology_scheme VALUES (?,?,?,?,?,?,?,?,?)", SCHEMES)

# Jones: migrate every existing event date, now attributed rather than anonymous.
rows=[]
for eid, sd in db.execute("SELECT event_id, start_date FROM event"):
    y=None
    if isinstance(sd,int): y=sd
    elif isinstance(sd,str):
        s=sd.strip()
        if s.lstrip("-").isdigit(): y=int(s)
        elif len(s)>=5 and s[:4].isdigit(): y=int(s[:4])   # '0054-05-03'
    if y is not None: rows.append((eid,"jones",y,None,"stated",None))
db.executemany("INSERT OR REPLACE INTO event_date VALUES (?,?,?,?,?,?)", rows)

# Ussher: ONLY dates traceable to a citable statement of his chronology.
# Anything not sourced is deliberately absent - an empty cell is honest, a
# guessed year is not.
USSHER=[
 (1,  -4004, "stated",     "First day of creation, 23 October 4004 BC (Julian)"),
 (71, -1922, "stated",     "Abraham's migration, ending the 2,082 years from creation"),
 (125,-1492, "derived",    "Implied by Ussher's 430 years from Abraham's departure from Haran"),
 (162,-1012, "stated",     "Foundations of Solomon's Temple, 480 years after the Exodus"),
 (254,-5,    "stated",     "Birth of Jesus, from Herod the Great's death in 4 BC"),
]
db.executemany("INSERT OR REPLACE INTO event_date VALUES (?,?,?,?,?,?)",
               [(e,"ussher",y,None,p,n) for e,y,p,n in USSHER])

# Thiele: the monarchy only. His division date differs from Jones's by 43 years,
# which is the single largest disagreement a reader of this app will meet.
THIELE=[
 (163,-931,"stated","Division of the kingdom; Rehoboam's reign in Judah begins 931/0 BC"),
 (164,-931,"stated","Death of Solomon, immediately preceding the division"),
 (165,-931,"stated","Reign of Rehoboam begins 931/0 BC"),
 (166,-931,"stated","Division of the kingdom; the northern kingdom begins"),
 (167,-931,"stated","Reign of Jeroboam I begins 931/0 BC"),
]
db.executemany("INSERT OR REPLACE INTO event_date VALUES (?,?,?,?,?,?)",
               [(e,"thiele",y,None,p,n) for e,y,p,n in THIELE])

# Mainstream critical: only dates fixed by records outside the Bible.
CRITICAL=[
 (163,-931,"stated","Division of the kingdom, following Thiele's synchronisms"),
 (164,-931,"stated","Death of Solomon"),
 (166,-931,"stated","Northern kingdom begins"),
]
db.executemany("INSERT OR REPLACE INTO event_date VALUES (?,?,?,?,?,?)",
               [(e,"critical",y,None,p,n) for e,y,p,n in CRITICAL])

NOTES=[
 ("why","Why the dates differ",
  "There is no single biblical chronology, and any app that shows you one date without "
  "saying whose it is has made a choice on your behalf.\n\n"
  "The disagreements come from three places. First, the manuscript traditions differ: the "
  "Hebrew Masoretic Text, the Greek Septuagint and the Samaritan Pentateuch give different "
  "ages in the genealogies of Genesis 5 and 11, and the Septuagint adds an ancestor after the "
  "flood. Those differences alone move creation by well over a thousand years.\n\n"
  "Second, chronologists disagree about whether the genealogies are continuous. Read as an "
  "unbroken father-to-son chain, they yield a creation around 4000 BC. Read as a selective "
  "list that skips generations - a normal practice in ancient genealogy - they yield no total "
  "at all.\n\n"
  "Third, the regnal records in Kings and Chronicles are genuinely hard. Reigns are counted "
  "differently in Israel and Judah, co-regencies overlap, and the two books sometimes "
  "disagree. Reconciling them is the problem Edwin Thiele spent a career on.",1),
 ("anchors","What is actually fixed",
  "Not everything is contested. From the divided monarchy onward, the biblical narrative can "
  "be tied to Assyrian and Babylonian records that carry their own dates, and the agreement "
  "is broadly good.\n\n"
  "The later the event, the firmer the ground. The fall of Jerusalem to Babylon and the edict "
  "of Cyrus permitting the return are fixed within a year or two by external sources, and "
  "essentially every scheme agrees about them. The uncertainty is concentrated in the "
  "primeval history and the patriarchs, where there is nothing outside the text to check "
  "against.",2),
 ("coverage","Why some schemes show no date",
  "The event timeline in this app was compiled under one scheme, Floyd Nolen Jones's, so that "
  "is the only one with a date for all 450 events. Other schemes carry only the dates that "
  "can be traced to a published statement of that chronology.\n\n"
  "Where a scheme has no date for an event, the app says so. It does not quietly fall back to "
  "another scheme's number and present it as that scheme's answer. A blank is information.",3),
 ("choosing","Which should you use",
  "If you want the chronology printed in the margins of a King James Bible, choose Ussher. If "
  "you want a modern conservative reckoning of the same kind, Jones is the default here and "
  "differs from Ussher by only a year or two at most points.\n\n"
  "If you are reading alongside academic commentary, the critical scheme will match what you "
  "find there, at the cost of offering no dates for the earliest chapters. None of these is "
  "the app's opinion. The choice is yours and you can change it at any time.",4),
]
db.executemany("INSERT INTO chronology_note VALUES (?,?,?,?)", NOTES)

db.executescript("""
CREATE INDEX IF NOT EXISTS ix_ed_scheme ON event_date(scheme_id, start_year);
CREATE INDEX IF NOT EXISTS ix_ed_event  ON event_date(event_id);
DROP VIEW IF EXISTS event_in_scheme;
-- One row per event per scheme. start_year IS NULL means that scheme has no
-- date for that event; it never borrows another scheme's number.
CREATE VIEW event_in_scheme AS
SELECT e.event_id, e.title, s.scheme_id, s.name AS scheme_name,
       d.start_year, d.precision, d.note
FROM event e CROSS JOIN chronology_scheme s
LEFT JOIN event_date d ON d.event_id=e.event_id AND d.scheme_id=s.scheme_id;
""")
db.commit()

print("schemes:")
for r in db.execute("""SELECT s.scheme_id, s.name, s.coverage,
                         (SELECT COUNT(*) FROM event_date d WHERE d.scheme_id=s.scheme_id)
                       FROM chronology_scheme s ORDER BY s.sort_order"""):
    print(f"  {r[0]:11s} {r[1]:26s} {r[2]:8s} {r[3]:>4} dated events")
print(f"\nevent_date rows: {db.execute('SELECT COUNT(*) FROM event_date').fetchone()[0]:,}")
print(f"explainer notes: {db.execute('SELECT COUNT(*) FROM chronology_note').fetchone()[0]}")
print("\nCreation and the Exodus across schemes:")
for r in db.execute("""SELECT title, scheme_name, start_year, precision FROM event_in_scheme
                       WHERE event_id IN (1,125) ORDER BY event_id, scheme_id"""):
    y = f"{abs(r[2])} BC" if r[2] is not None and r[2]<0 else (str(r[2]) if r[2] is not None else "— no date in this scheme")
    print(f"  {r[0][:26]:28s} {r[1]:26s} {y:<24} {r[3] or ''}")
db.close()
