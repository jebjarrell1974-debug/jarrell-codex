# -*- coding: utf-8 -*-
"""Generate the static site data: one file per chapter, plus shared lookups.

Compact positional arrays rather than keyed objects - the key names would
otherwise repeat 450,000 times. A phone fetches one chapter at a time
(~60-90 KB gzipped) plus the shared lexicon once, so the whole Bible is
usable over a bad connection without ever downloading all of it.
"""
import json, os, sqlite3, gzip, shutil
DB="/home/claude/bible/build/bible.db"
OUT="/home/claude/site"
db=sqlite3.connect(DB); db.row_factory=sqlite3.Row
q=lambda s,*p: db.execute(s,p).fetchall()
J=lambda o: json.dumps(o, ensure_ascii=False, separators=(",",":"))

if os.path.exists(OUT): shutil.rmtree(OUT)
os.makedirs(f"{OUT}/data/ch", exist_ok=True)

# ---- shared: books, lexicon, morph codes, schemes
books=[]
for r in q("""SELECT book, book_order, testament, MAX(chapter) chapters
              FROM verse GROUP BY book ORDER BY book_order"""):
    books.append([r["book"], r["book_order"], r["testament"], r["chapters"]])
names={}
for r in q("SELECT name, book FROM book_name"): names.setdefault(r["book"], []).append(r["name"])
open(f"{OUT}/data/books.json","w",encoding="utf-8").write(J({"books":books,"names":names}))

lex={}
for r in q("""SELECT l.strongs, l.lemma, l.translit, l.gloss, l.definition,
                     f.entry AS full
              FROM lexicon l LEFT JOIN lexicon_full f ON f.strongs=l.strongs"""):
    lex[r["strongs"]]=[r["lemma"], r["translit"], r["gloss"],
                       (r["definition"] or "")[:1200],
                       (r["full"] or "")[:3000] or None]
open(f"{OUT}/data/lexicon.json","w",encoding="utf-8").write(J(lex))

morph={r["code"]: r["description"] for r in q("SELECT code, description FROM morph_code")}
open(f"{OUT}/data/morph.json","w",encoding="utf-8").write(J(morph))

schemes=[dict(r) for r in q("""SELECT scheme_id,name,coverage,summary,source,is_default
                               FROM chronology_scheme ORDER BY sort_order""")]
notes_c=[dict(r) for r in q("SELECT heading,body FROM chronology_note ORDER BY sort_order")]
open(f"{OUT}/data/chronology.json","w",encoding="utf-8").write(J({"schemes":schemes,"notes":notes_c}))

# ---- per chapter
# token:  [position, surface, translit, gloss, lang, [[strongs, morphcode, simple], ...]]
# verse:  {n, t:[tokens], x:{code:text}, p:[places], pe:[people], ev:[events], nt:[notes], xr:[refs]}
total=0; biggest=0; chapters=0
for b in q("SELECT DISTINCT book, book_order FROM verse ORDER BY book_order"):
    book=b["book"]
    for c in q("SELECT DISTINCT chapter FROM verse WHERE book=? ORDER BY chapter", book):
        ch=c["chapter"]; verses=[]
        for v in q("""SELECT verse_key, verse FROM verse WHERE book=? AND chapter=?
                      ORDER BY verse""", book, ch):
            vk=v["verse_key"]
            toks=[]
            for t in q("""SELECT token_id,position,surface,translit,gloss,language
                          FROM token WHERE verse_key=?
                            AND (text_type GLOB 'L*' OR text_type GLOB '*N*')
                          ORDER BY position""", vk):
                ms=[[m["strongs"], m["morph_code"], m["strongs_simple"]]
                    for m in q("SELECT strongs,morph_code,strongs_simple FROM morpheme "
                               "WHERE token_id=? ORDER BY seq", t["token_id"])]
                toks.append([t["position"], t["surface"], t["translit"], t["gloss"],
                             t["language"], ms])
            rec={"n": v["verse"], "t": toks,
                 "x": {r["code"]: r["text"] for r in
                       q("SELECT code,text FROM translation_verse WHERE canonical_key=?", vk)}}
            pl=[[r["name"], r["status"], r["latitude"], r["longitude"]] for r in
                q("""SELECT p.name,p.status,p.latitude,p.longitude FROM place p
                     JOIN place_verse pv USING(place_id) WHERE pv.verse_key=? ORDER BY p.name""", vk)]
            if pl: rec["p"]=pl
            pe=[r["name"] for r in q("""SELECT p.name FROM person p JOIN person_verse pv
                 USING(person_id) WHERE pv.verse_key=? ORDER BY p.name""", vk)]
            if pe: rec["pe"]=pe
            ev=[[r["event_id"], r["title"]] for r in q("""SELECT e.event_id,e.title FROM event e
                 JOIN event_verse ev ON ev.event_id=e.event_id WHERE ev.verse_key=?
                 ORDER BY e.sort_key""", vk)]
            if ev:
                rec["ev"]=ev
                rec["ed"]={}
                for eid,_ in ev:
                    rec["ed"][str(eid)]={r["scheme_id"]: r["start_year"] for r in
                        q("""SELECT s.scheme_id, d.start_year FROM chronology_scheme s
                             LEFT JOIN event_date d ON d.event_id=? AND d.scheme_id=s.scheme_id""", eid)}
            nt=[[r["quote"], r["category"], r["body"]] for r in
                q("SELECT quote,category,body FROM note WHERE verse_key=? LIMIT 12", vk)]
            if nt: rec["nt"]=nt
            xr=[[r["to_key"], r["votes"]] for r in
                q("""SELECT to_key,votes FROM xref WHERE from_key=?
                     ORDER BY votes DESC LIMIT 12""", vk)]
            if xr: rec["xr"]=xr
            sem={r["position"]: r["role"] for r in
                 q("SELECT position,role FROM semantics WHERE verse_key=? AND role IS NOT NULL", vk)}
            if sem: rec["sr"]={str(k):v for k,v in sem.items()}
            verses.append(rec)
        blob=J({"b":book,"c":ch,"v":verses}).encode("utf-8")
        with open(f"{OUT}/data/ch/{book}.{ch}.json","wb") as fh: fh.write(blob)
        total+=len(blob); biggest=max(biggest,len(blob)); chapters+=1

print(f"chapters written: {chapters:,}")
print(f"total chapter data: {total/1e6:.1f} MB  (largest chapter {biggest/1024:.0f} KB)")
for f in ["books.json","lexicon.json","morph.json","chronology.json"]:
    print(f"  {f:18s} {os.path.getsize(f'{OUT}/data/{f}')/1e6:.1f} MB")
tot=total+sum(os.path.getsize(f"{OUT}/data/{f}") for f in
              ["books.json","lexicon.json","morph.json","chronology.json"])
print(f"site data total: {tot/1e6:.1f} MB")
db.close()
