"""Parse TVTMS $Section blocks into a tradition -> English verse mapping."""
import re, sqlite3, glob
DB="/home/claude/bible/build/bible.db"
V=glob.glob("/home/claude/bible/sources/stepbible/Versification/TVTMS*.txt")[0]

BK=re.compile(r'^([1-5A-Za-z]{2,3})\.(\d+)[:.](\d+)(?:\.(\d+))?(?:-(\d+))?$')
ACTIONS={"OneToOne","MergedPrevVerse","MergedFollVerse","TextMayBeMissing",
         "KeepVerse","RenumberVerse","IfEmptyVerse","Psalm"}

def expand(ref):
    """'Gen.32:1-32' -> ['Gen.32.1'...'Gen.32.32'];  'Gen.5:31.2' -> ['Gen.5.31.2']"""
    ref=ref.strip()
    if not ref or ref.lower().startswith("absent") or "=" in ref: return []
    ref=ref.lstrip("*").strip()
    m=BK.match(ref)
    if not m: return []
    bk,ch,v1,sub,v2=m.groups()
    if v2:
        return [f"{bk}.{ch}.{n}" for n in range(int(v1),int(v2)+1)]
    return [f"{bk}.{ch}.{v1}" + (f".{sub}" if sub else "")]

rows=[]; cols=None; nsec=0
for line in open(V,encoding="utf-8-sig"):
    c=[x.strip() for x in line.rstrip("\n").split("\t")]
    if not c or not c[0]: continue
    if c[0].startswith("$"):
        if len(c)>1 and any(h for h in c[1:]):
            cols=c[1:]; nsec+=1
        continue
    if cols is None: continue
    act=c[0].strip()
    if act.startswith("TEST") or act.startswith("'") or act==",": continue
    base=act.split()[0] if act else ""
    if base not in ACTIONS: continue
    vals=c[1:len(cols)+1]
    if not vals: continue
    eng=expand(vals[0]) if vals else []
    for ci,trad in enumerate(cols):
        if ci==0 or not trad or ci>=len(vals): continue
        t=re.sub(r'\s*\(.*\)$','',trad).strip()
        if not t or t.lower().startswith("unidivided or"): continue
        other=expand(vals[ci])
        if not eng or not other: continue
        if len(eng)==len(other):
            pairs=zip(other,eng)
        elif len(other)==1 and len(eng)>=1:
            pairs=((other[0],eng[0]),)
        elif len(eng)==1:
            pairs=((o,eng[0]) for o in other)
        else:
            continue
        for o,e in pairs:
            rows.append((t,o,e,base))

db=sqlite3.connect(DB)
db.executescript("""
DROP TABLE IF EXISTS versification;
CREATE TABLE versification(
  tradition TEXT, tradition_ref TEXT, english_ref TEXT, relation TEXT,
  PRIMARY KEY(tradition, tradition_ref, english_ref));
CREATE INDEX ix_vers_trad ON versification(tradition, tradition_ref);
CREATE INDEX ix_vers_eng  ON versification(english_ref);
""")
db.executemany("INSERT OR IGNORE INTO versification VALUES (?,?,?,?)", rows)
db.commit()
print(f"sections parsed: {nsec}   mapping rows: {db.execute('SELECT COUNT(*) FROM versification').fetchone()[0]:,}")
for t,n in db.execute("SELECT tradition, COUNT(*) FROM versification GROUP BY 1 ORDER BY 2 DESC LIMIT 8"):
    print(f"  {t:22s} {n:,}")
print("\n2Co.13 mappings:")
for r in db.execute("""SELECT tradition, tradition_ref, english_ref, relation FROM versification
                       WHERE tradition_ref LIKE '2Co.13.%' OR english_ref LIKE '2Co.13.%'"""):
    print("   ",r)
db.close()
