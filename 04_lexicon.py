"""Load TBESH/TBESG into a lexicon table keyed on disambiguated Strong's."""
import re, sqlite3, glob, html
DB="/home/claude/bible/build/bible.db"
LEX="/home/claude/bible/sources/stepbible/Lexicons"
ROW=re.compile(r'^([HG]\d{4}[A-Za-z]?)\t')

def clean(s):
    s=re.sub(r"<ref='[^']*'>(.*?)</ref>", r"\1", s)
    s=re.sub(r'<br\s*/?>', ' | ', s, flags=re.I)
    s=re.sub(r'<[^>]+>', '', s)
    return html.unescape(re.sub(r'\s{2,}',' ',s)).strip()

rows={}
for path in glob.glob(LEX+"/TBESH*.txt")+glob.glob(LEX+"/TBESG*.txt"):
    lang="H" if "TBESH" in path else "G"
    for line in open(path, encoding="utf-8-sig"):
        if not ROW.match(line): continue
        c=line.rstrip("\n").split("\t")
        if len(c)<8: continue
        estrong=c[0].strip()
        dstrong=c[1].split("=")[0].strip() or estrong
        ustrong=c[2].strip() or None
        key=dstrong
        if key in rows: continue
        rows[key]=(key, estrong, ustrong, lang, c[3].strip(), c[4].strip(),
                   c[5].strip(), c[6].strip(), clean(c[7])[:4000])

db=sqlite3.connect(DB)
db.executescript("""
DROP TABLE IF EXISTS lexicon;
CREATE TABLE lexicon(
  strongs TEXT PRIMARY KEY, estrong TEXT, ustrong TEXT, language TEXT,
  lemma TEXT, translit TEXT, morph_class TEXT, gloss TEXT, definition TEXT);
""")
db.executemany("INSERT INTO lexicon VALUES (?,?,?,?,?,?,?,?,?)", rows.values())
db.commit()
print(f"lexicon entries: {len(rows):,}")

tot,hit=0,0; miss={}
for strongs,n in db.execute("""SELECT strongs, COUNT(*) FROM morpheme
                               WHERE strongs IS NOT NULL GROUP BY 1"""):
    tot+=n
    r=db.execute("SELECT 1 FROM lexicon WHERE strongs=?",(strongs,)).fetchone()
    if not r:
        base=re.sub(r'^([HG]\d{4}).*$',r'\1',strongs)
        r=db.execute("SELECT 1 FROM lexicon WHERE strongs=? OR estrong=?",(base,base)).fetchone()
    if r: hit+=n
    else: miss[strongs]=n
print(f"morphemes with a lexicon entry: {hit:,}/{tot:,} ({100*hit/tot:.2f}%)")
if miss:
    top=sorted(miss.items(), key=lambda x:-x[1])[:10]
    print(f"unmatched distinct Strong's: {len(miss)}  top: {top}")
db.close()
