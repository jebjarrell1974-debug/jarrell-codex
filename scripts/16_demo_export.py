# -*- coding: utf-8 -*-
"""Export a real, fully-resolved slice for the reference reader UI."""
import sqlite3, json, re
DB="/home/claude/bible/build/bible.db"
c=sqlite3.connect(DB); c.row_factory=sqlite3.Row
def rows(q,*p): return [dict(r) for r in c.execute(q,p)]

def short(s,n=240):
    if not s: return None
    s=re.sub(r'\s+',' ',s).strip()
    return s if len(s)<=n else s[:n].rsplit(' ',1)[0]+'…'

out={"chapters":[], "schemes":rows(
  "SELECT scheme_id,name,coverage,summary,source,is_default FROM chronology_scheme ORDER BY sort_order"),
  "notes":rows("SELECT heading,body FROM chronology_note ORDER BY sort_order")}

for book,chap,label in [("Gen",1,"Genesis 1"),("Jhn",1,"John 1"),("Act",17,"Acts 17")]:
    toks=rows("""SELECT t.token_id,t.verse_key,t.position,t.surface,t.translit,t.gloss,t.language
                 FROM token t JOIN verse v USING(verse_key)
                 WHERE v.book=? AND v.chapter=? AND (t.text_type GLOB 'L*' OR t.text_type GLOB '*N*')
                 ORDER BY v.verse,t.position""",book,chap)
    verses={}
    for t in toks:
        m=rows("""SELECT m.seq,m.surface,m.strongs,m.strongs_simple,m.morph_code,
                         mc.description AS parsing, l.lemma,l.gloss,l.definition
                  FROM morpheme m LEFT JOIN morph_code mc ON mc.code=m.morph_code
                  LEFT JOIN lexicon l ON l.strongs=m.strongs
                  WHERE m.token_id=? ORDER BY m.seq""",t["token_id"])
        for x in m:
            x["definition"]=short(x.get("definition"))
            x["count"]=c.execute("SELECT COUNT(*) FROM morpheme WHERE strongs_simple=?",
                                 (x["strongs_simple"],)).fetchone()[0] if x["strongs_simple"] else 0
        t["morphemes"]=m
        verses.setdefault(t["verse_key"],{"verse_key":t["verse_key"],"tokens":[]})["tokens"].append(t)
    for vk,v in verses.items():
        v["translations"]=rows("SELECT code,text FROM translation_verse WHERE canonical_key=? ORDER BY code",vk)
        v["places"]=rows("""SELECT p.name,p.status,p.latitude,p.longitude,p.modern_name,p.wikidata
                            FROM place p JOIN place_verse pv USING(place_id) WHERE pv.verse_key=? ORDER BY p.name""",vk)
        v["people"]=rows("""SELECT p.name,p.birth_year,p.death_year FROM person p
                            JOIN person_verse pv USING(person_id) WHERE pv.verse_key=? ORDER BY p.name""",vk)
        v["events"]=rows("""SELECT e.event_id,e.title FROM event e JOIN event_verse ev ON ev.event_id=e.event_id
                            WHERE ev.verse_key=? ORDER BY e.sort_key""",vk)
        for e in v["events"]:
            e["dates"]=rows("""SELECT s.scheme_id,s.name,d.start_year,d.precision
                               FROM chronology_scheme s
                               LEFT JOIN event_date d ON d.event_id=? AND d.scheme_id=s.scheme_id
                               ORDER BY s.sort_order""",e["event_id"])
    out["chapters"].append({"book":book,"chapter":chap,"label":label,
                            "verses":list(verses.values())})

p="/home/claude/bible/build/demo.json"
json.dump(out,open(p,"w",encoding="utf-8"),ensure_ascii=False,separators=(",",":"))
import os
print(f"wrote {p}  {os.path.getsize(p)/1024:.0f} KB")
for ch in out["chapters"]:
    nt=sum(len(v['tokens']) for v in ch['verses'])
    print(f"  {ch['label']:12s} {len(ch['verses']):>3} verses  {nt:>4} words")
c.close()
