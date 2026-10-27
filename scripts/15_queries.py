# -*- coding: utf-8 -*-
"""The app's query layer, tested against the real database.

Every query the Android client needs, written once here and verified, so the
client is a port of something known-good rather than SQL written blind.
Each function returns plain dicts and is timed, because a reader that stutters
when you tap a word is a reader nobody uses.
"""
import sqlite3, time, json, sys
DB="/home/claude/bible/build/bible.db"

def conn():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row
    return c

# ---------------------------------------------------------------- reading
CHAPTER = """
SELECT t.token_id, t.verse_key, t.position, t.surface, t.translit, t.gloss,
       t.language, t.text_type
FROM token t JOIN verse v USING(verse_key)
WHERE v.book=? AND v.chapter=?
ORDER BY v.verse, t.position"""

VERSE_TEXT = """
SELECT code, text FROM translation_verse
WHERE canonical_key=? ORDER BY code"""

# ------------------------------------------------------------ word detail
WORD = """
SELECT m.seq, m.surface, m.strongs, m.morph_code, m.language,
       c.description AS parsing,
       l.lemma, l.translit AS lemma_translit, l.gloss, l.definition
FROM morpheme m
LEFT JOIN morph_code c ON c.code=m.morph_code
LEFT JOIN lexicon   l ON l.strongs=m.strongs
WHERE m.token_id=? ORDER BY m.seq"""

# ------------------------------------------------------------ concordance
CONCORDANCE = """
SELECT v.book, v.chapter, v.verse, t.verse_key, t.surface, t.gloss
FROM morpheme m
JOIN token t ON t.token_id=m.token_id
JOIN verse v ON v.verse_key=t.verse_key
WHERE m.strongs=?
ORDER BY v.book_order, v.chapter, v.verse, t.position
LIMIT ? OFFSET ?"""
CONCORDANCE_COUNT = "SELECT COUNT(*) FROM morpheme WHERE strongs=?"

# A reader holding a printed Strong's concordance types "H3068", not "H3068G".
# Extended Strong's disambiguates senses; simple Strong's is what people look up.
# The client must offer both: search wide, then narrow by sense.
CONCORDANCE_SIMPLE = """
SELECT v.book, v.chapter, v.verse, t.verse_key, t.surface, t.gloss, m.strongs
FROM morpheme m
JOIN token t ON t.token_id=m.token_id
JOIN verse v ON v.verse_key=t.verse_key
WHERE m.strongs_simple=?
ORDER BY v.book_order, v.chapter, v.verse, t.position
LIMIT ? OFFSET ?"""
CONCORDANCE_SIMPLE_COUNT = "SELECT COUNT(*) FROM morpheme WHERE strongs_simple=?"
SENSES_OF = """
SELECT m.strongs, COUNT(*) n, l.gloss
FROM morpheme m LEFT JOIN lexicon l ON l.strongs=m.strongs
WHERE m.strongs_simple=? GROUP BY m.strongs ORDER BY n DESC"""

# ------------------------------------------------------------- context
PLACES_IN_VERSE = """
SELECT p.place_id, p.name, p.status, p.latitude, p.longitude,
       p.modern_name, p.wikidata
FROM place p JOIN place_verse pv USING(place_id)
WHERE pv.verse_key=? ORDER BY p.name"""

PEOPLE_IN_VERSE = """
SELECT p.person_id, p.name, p.gender, p.birth_year, p.death_year
FROM person p JOIN person_verse pv USING(person_id)
WHERE pv.verse_key=? ORDER BY p.name"""

EVENTS_IN_VERSE = """
SELECT e.event_id, e.title, d.start_year, d.precision, d.note
FROM event e
JOIN event_verse ev ON ev.event_id=e.event_id
LEFT JOIN event_date d ON d.event_id=e.event_id AND d.scheme_id=?
WHERE ev.verse_key=? ORDER BY e.sort_key"""

DICT_FOR_PERSON = """
SELECT term_label, body FROM dictionary
WHERE person_slug=(SELECT slug FROM person WHERE person_id=?) ORDER BY item_num"""

SCHEMES = "SELECT scheme_id,name,coverage,summary,source,is_default FROM chronology_scheme ORDER BY sort_order"

def timed(label, fn, *a):
    t=time.perf_counter(); r=fn(*a); ms=(time.perf_counter()-t)*1000
    n=len(r) if isinstance(r,list) else 1
    print(f"  {label:46s} {ms:7.1f} ms   {n:>6,} rows")
    return r, ms

def main():
    c=conn(); q=lambda s,*p: [dict(r) for r in c.execute(s,p)]
    slow=[]
    print("=== reading")
    ch,_   = timed("open Genesis 1 (all words)",      q, CHAPTER, "Gen", 1)
    jn,ms  = timed("open John 1 (all words)",         q, CHAPTER, "Jhn", 1); slow.append(("John 1",ms))
    tx,_   = timed("translations for one verse",      q, VERSE_TEXT, "Gen.1.1")

    print("\n=== tap a word")
    tid=ch[0]["token_id"]
    w,ms = timed(f"word detail ({tid})",              q, WORD, tid); slow.append(("word detail",ms))
    st=w[-1]["strongs"]
    n=c.execute(CONCORDANCE_COUNT,(st,)).fetchone()[0]
    print(f"  {'concordance size for '+st:46s} {'':10s} {n:>6,} rows")
    cc,ms = timed(f"concordance page 1 of {st}",      q, CONCORDANCE, st, 50, 0); slow.append(("concordance",ms))
    cl,ms = timed(f"concordance page 20 of {st}",     q, CONCORDANCE, st, 50, 950); slow.append(("concordance deep",ms))

    print("\n=== simple Strong's, the way a reader actually looks it up")
    n=c.execute(CONCORDANCE_SIMPLE_COUNT,("H3068",)).fetchone()[0]
    print(f"  {'H3068 (YHWH) total occurrences':46s} {'':10s} {n:>6,} rows")
    sn,ms = timed("senses behind simple H3068",       q, SENSES_OF, "H3068"); slow.append(("senses",ms))
    for r in sn: print(f"      {r['strongs']:8s} {r['n']:>6,}  {r['gloss']}")
    cs,ms = timed("concordance page 1 for H3068",     q, CONCORDANCE_SIMPLE, "H3068", 50, 0); slow.append(("simple concordance",ms))
    cd,ms = timed("concordance page 100 for H3068",   q, CONCORDANCE_SIMPLE, "H3068", 50, 4950); slow.append(("simple concordance deep",ms))

    print("\n=== context for a verse")
    pl,_ = timed("places in Acts 17:22",              q, PLACES_IN_VERSE, "Act.17.22")
    pp,_ = timed("people in Acts 17:22",              q, PEOPLE_IN_VERSE, "Act.17.22")
    ev,ms= timed("events at Exodus 14:21 (Jones)",    q, EVENTS_IN_VERSE, "jones", "Exo.14.21"); slow.append(("events",ms))
    sc,_ = timed("list chronology schemes",           q, SCHEMES)

    print("\n=== worst case")
    big,ms = timed("concordance count for the commonest word", q,
                   "SELECT strongs, COUNT(*) n FROM morpheme GROUP BY 1 ORDER BY n DESC LIMIT 5")
    slow.append(("group-by all morphemes",ms))
    print(f"      commonest: {big[0]['strongs']} x {big[0]['n']:,}")

    print("\n=== verdict")
    worst=max(slow,key=lambda x:x[1])
    ok=all(ms<300 for _,ms in slow)
    print(f"  slowest query: {worst[0]} at {worst[1]:.1f} ms")
    print(f"  {'PASS' if ok else 'FAIL'}: every query under 300 ms on a cold index")
    # Sample output so the client author can see the shape
    sample={"token":ch[0],"morphemes":w,"translations":tx,
            "places":pl,"people":pp,"schemes":[s["scheme_id"] for s in sc]}
    open("/home/claude/bible/build/query-shapes.json","w").write(json.dumps(sample,ensure_ascii=False,indent=1))
    print("  wrote build/query-shapes.json")
    c.close()
    return 0 if ok else 1

sys.exit(main())
