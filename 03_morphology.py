"""Build morph_code lookup from TEHMC/TEGMC and attach indexable parsing columns."""
import re, sqlite3, collections, glob
DB="/home/claude/bible/build/bible.db"
MC="/home/claude/bible/sources/stepbible/Morphology codes"

KEYMAP={ "function":"pos","form":"form","gender":"gender","number":"number","state":"state",
         "case":"case","tense":"tense","voice":"voice","mood":"mood","person":"person",
         "stem":"stem","degree":"degree","name type":"name_type","type":"subtype" }

def load(path, lang):
    rows={}
    for line in open(path, encoding="utf-8-sig"):
        if "\t" not in line: continue
        code, _, rest = line.rstrip("\n").partition("\t")
        code=code.strip(); rest=rest.strip()
        if not code or "=" not in rest: continue
        if re.search(r'[\s]', code): continue
        attrs={}
        for part in rest.split(";"):
            if "=" not in part: continue
            k,_,v=part.partition("=")
            k=k.strip().lower(); v=v.strip()
            if k in KEYMAP and v: attrs[KEYMAP[k]]=v
        if attrs: rows[code]=(lang, rest, attrs)
    return rows

codes={}
for f in glob.glob(MC+"/TEHMC*.txt"): codes.update(load(f,"H"))
for f in glob.glob(MC+"/TEGMC*.txt"): codes.update(load(f,"G"))

db=sqlite3.connect(DB)
db.executescript("""
DROP TABLE IF EXISTS morph_code;
CREATE TABLE morph_code(
  code TEXT PRIMARY KEY, language TEXT, description TEXT,
  pos TEXT, form TEXT, gender TEXT, number TEXT, state TEXT, "case" TEXT,
  tense TEXT, voice TEXT, mood TEXT, person TEXT, stem TEXT, degree TEXT,
  name_type TEXT, subtype TEXT);
""")
cols=["pos","form","gender","number","state","case","tense","voice","mood","person","stem","degree","name_type","subtype"]
db.executemany(f'INSERT INTO morph_code VALUES (?,?,?,{",".join("?"*len(cols))})',
    [(c, lang, desc, *[a.get(k) for k in cols]) for c,(lang,desc,a) in codes.items()])
db.commit()
print(f"morph codes loaded: {len(codes):,}  (H={sum(1 for v in codes.values() if v[0]=='H'):,}  G={sum(1 for v in codes.values() if v[0]=='G'):,})")

# coverage: morpheme.morph_code was stored WITHOUT the H/A language prefix for Hebrew
cur=db.execute("""SELECT language, morph_code, COUNT(*) FROM morpheme
                  WHERE morph_code IS NOT NULL AND morph_code<>'' GROUP BY 1,2""")
have=set(codes)
tot=collections.Counter(); hit=collections.Counter(); miss=collections.Counter()
for lang, mc, n in cur:
    tot[lang]+=n
    cands=[mc, "H"+mc, "A"+mc] if lang in ("H","A") else [mc]
    if any(c in have for c in cands): hit[lang]+=n
    else: miss[mc]+=n
for lang in sorted(tot):
    pct=100*hit[lang]/tot[lang] if tot[lang] else 0
    print(f"  {lang}: {hit[lang]:,}/{tot[lang]:,} morphemes resolved ({pct:.2f}%)")
if miss:
    print(f"  unresolved distinct codes: {len(miss)}  top:", miss.most_common(8))
db.close()
