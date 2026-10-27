"""Cross-check Hebrew token counts against OpenScriptures WLC XML (MACULA's upstream)."""
import re, glob, sqlite3, collections, os, xml.etree.ElementTree as ET
DB="/home/claude/bible/build/bible.db"
XD="/home/claude/bible/sources/macula-hebrew/sources/OpenScriptures/xml"
MAP={"Gen":"Gen","Exod":"Exo","Lev":"Lev","Num":"Num","Deut":"Deu","Josh":"Jos","Judg":"Jdg",
"Ruth":"Rut","1Sam":"1Sa","2Sam":"2Sa","1Kgs":"1Ki","2Kgs":"2Ki","1Chr":"1Ch","2Chr":"2Ch",
"Ezra":"Ezr","Neh":"Neh","Esth":"Est","Job":"Job","Ps":"Psa","Prov":"Pro","Eccl":"Ecc",
"Song":"Sng","Isa":"Isa","Jer":"Jer","Lam":"Lam","Ezek":"Ezk","Dan":"Dan","Hos":"Hos",
"Joel":"Jol","Amos":"Amo","Obad":"Oba","Jonah":"Jon","Mic":"Mic","Nah":"Nam","Hab":"Hab",
"Zeph":"Zep","Hag":"Hag","Zech":"Zec","Mal":"Mal"}
oshb=collections.Counter()
for p in sorted(glob.glob(XD+"/*.xml")):
    stem=os.path.splitext(os.path.basename(p))[0]
    bk=MAP.get(stem)
    if not bk: print("  unmapped xml:", stem); continue
    n=0
    for _,el in ET.iterparse(p, events=("end",)):
        if el.tag.rsplit('}',1)[-1]=="m": n+=1; el.clear()
    oshb[bk]=n
print(f"OpenScriptures WLC: {sum(oshb.values()):,} <m> morphemes over {len(oshb)} books")

db=sqlite3.connect(DB)
# Our comparable set: Hebrew/Aramaic printed text (Leningrad + Qere), one row per word.
ours=collections.Counter(dict(db.execute("""
  SELECT v.book, COUNT(*) FROM morpheme m
  JOIN token t ON t.token_id=m.token_id JOIN verse v ON v.verse_key=t.verse_key
  WHERE t.language IN ('H','A') AND t.text_type GLOB 'L*'
  GROUP BY 1""")))
order=list(MAP.values())
print(f"\n{'book':5s} {'ours':>9s} {'OSHB':>9s} {'diff':>7s}")
diffs=0; tot=0
for b in order:
    d=ours.get(b,0)-oshb.get(b,0); tot+=abs(d)
    if d: diffs+=1; print(f"{b:5s} {ours.get(b,0):9,} {oshb.get(b,0):9,} {d:+7,}")
print(f"\nbooks: {len(order)}   differing: {diffs}   total abs diff: {tot:,}   ours={sum(ours.values()):,} oshb={sum(oshb.values()):,}")
db.close()
