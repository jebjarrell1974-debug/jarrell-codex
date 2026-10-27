"""Independent cross-check: per-book token counts, ours vs MACULA."""
import csv, re, sqlite3, collections, sys
DB="/home/claude/bible/build/bible.db"
HEB="/home/claude/bible/sources/macula-hebrew/WLC/tsv/macula-hebrew.tsv"
GRK="/home/claude/bible/sources/macula-greek/Nestle1904/tsv/macula-greek-Nestle1904.tsv"
USFM={"GEN":"Gen","EXO":"Exo","LEV":"Lev","NUM":"Num","DEU":"Deu","JOS":"Jos","JDG":"Jdg",
"RUT":"Rut","1SA":"1Sa","2SA":"2Sa","1KI":"1Ki","2KI":"2Ki","1CH":"1Ch","2CH":"2Ch","EZR":"Ezr",
"NEH":"Neh","EST":"Est","JOB":"Job","PSA":"Psa","PRO":"Pro","ECC":"Ecc","SNG":"Sng","ISA":"Isa",
"JER":"Jer","LAM":"Lam","EZK":"Ezk","DAN":"Dan","HOS":"Hos","JOL":"Jol","AMO":"Amo","OBA":"Oba",
"JON":"Jon","MIC":"Mic","NAM":"Nam","HAB":"Hab","ZEP":"Zep","HAG":"Hag","ZEC":"Zec","MAL":"Mal",
"MAT":"Mat","MRK":"Mrk","LUK":"Luk","JHN":"Jhn","ACT":"Act","ROM":"Rom","1CO":"1Co","2CO":"2Co",
"GAL":"Gal","EPH":"Eph","PHP":"Php","COL":"Col","1TH":"1Th","2TH":"2Th","1TI":"1Ti","2TI":"2Ti",
"TIT":"Tit","PHM":"Phm","HEB":"Heb","JAS":"Jas","1PE":"1Pe","2PE":"2Pe","1JN":"1Jn","2JN":"2Jn",
"3JN":"3Jn","JUD":"Jud","REV":"Rev"}
NUM2={str(i+1).zfill(2):b for i,b in enumerate(
 "Gen Exo Lev Num Deu Jos Jdg Rut 1Sa 2Sa 1Ki 2Ki 1Ch 2Ch Ezr Neh Est Job Psa Pro Ecc Sng Isa Jer Lam Ezk Dan Hos Jol Amo Oba Jon Mic Nam Hab Zep Hag Zec Mal".split())}
NUM2.update({str(i+40).zfill(2):b for i,b in enumerate(
 "Mat Mrk Luk Jhn Act Rom 1Co 2Co Gal Eph Php Col 1Th 2Th 1Ti 2Ti Tit Phm Heb Jas 1Pe 2Pe 1Jn 2Jn 3Jn Jud Rev".split())})

def book_of(val):
    if not val: return None
    v=str(val).strip()
    m=re.match(r'^([A-Z1-3]{3})\b', v)
    if m and m.group(1) in USFM: return USFM[m.group(1)]
    m=re.match(r'^n?(\d{2})\d{6,}', v)      # macula node ids: BBCCCVVVWWW
    if m and m.group(1) in NUM2: return NUM2[m.group(1)]
    return None

def count(path, label):
    c=collections.Counter(); hdr=None
    with open(path, encoding="utf-8", newline="") as fh:
        rd=csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
        hdr=next(rd)
        idx=None
        for cand in ("ref","xml:id","id","nodeId"):
            if cand in hdr: idx=hdr.index(cand); break
        if idx is None: idx=0
        for row in rd:
            if not row or idx>=len(row): continue
            b=book_of(row[idx])
            if b: c[b]+=1
    print(f"{label}: {sum(c.values()):,} rows over {len(c)} books (key column '{hdr[idx] if hdr else '?'}')")
    return c

mac=count(HEB,"MACULA Hebrew"); mac.update(count(GRK,"MACULA Greek N1904"))
db=sqlite3.connect(DB)
ours=collections.Counter(dict(db.execute("SELECT v.book, COUNT(*) FROM token t JOIN verse v USING(verse_key) GROUP BY 1")))
# restrict to the text types a single edition would print
ours_n=collections.Counter(dict(db.execute("""
  SELECT v.book, COUNT(*) FROM token t JOIN verse v USING(verse_key)
  WHERE (t.language='G' AND t.text_type GLOB '*N*' AND t.text_type NOT GLOB '*(*N*)*')
     OR (t.language IN ('H','A') AND t.text_type GLOB 'L*')
  GROUP BY 1""")))
print(f"\n{'book':5s} {'ours(all)':>10s} {'ours(base)':>11s} {'macula':>8s} {'diff':>7s}")
tot_d=0; shown=0
for b in sorted(set(mac)|set(ours), key=lambda x: list(NUM2.values()).index(x) if x in NUM2.values() else 99):
    d=ours_n.get(b,0)-mac.get(b,0); tot_d+=abs(d)
    if d!=0 and shown<18:
        print(f"{b:5s} {ours.get(b,0):10,} {ours_n.get(b,0):11,} {mac.get(b,0):8,} {d:+7,}"); shown+=1
print(f"\nbooks compared: {len(set(mac)&set(ours))}   books differing: {sum(1 for b in set(mac)|set(ours) if ours_n.get(b,0)!=mac.get(b,0))}")
print(f"total absolute difference: {tot_d:,}")
db.close()
