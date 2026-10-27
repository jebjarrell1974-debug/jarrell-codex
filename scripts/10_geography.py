"""Ingest OpenBible.info geocoding data: places, coordinates, confidence, verse links."""
import json, re, sqlite3, os
DB="/home/claude/bible/build/bible.db"
D="/home/claude/bible/sources/Bible-Geocoding-Data/data"
USFM={"GEN":"Gen","EXO":"Exo","LEV":"Lev","NUM":"Num","DEU":"Deu","JOS":"Jos","JDG":"Jdg",
"RUT":"Rut","1SA":"1Sa","2SA":"2Sa","1KI":"1Ki","2KI":"2Ki","1CH":"1Ch","2CH":"2Ch","EZR":"Ezr",
"NEH":"Neh","EST":"Est","JOB":"Job","PSA":"Psa","PRO":"Pro","ECC":"Ecc","SNG":"Sng","ISA":"Isa",
"JER":"Jer","LAM":"Lam","EZK":"Ezk","DAN":"Dan","HOS":"Hos","JOL":"Jol","AMO":"Amo","OBA":"Oba",
"JON":"Jon","MIC":"Mic","NAM":"Nam","HAB":"Hab","ZEP":"Zep","HAG":"Hag","ZEC":"Zec","MAL":"Mal",
"MAT":"Mat","MRK":"Mrk","LUK":"Luk","JHN":"Jhn","ACT":"Act","ROM":"Rom","1CO":"1Co","2CO":"2Co",
"GAL":"Gal","EPH":"Eph","PHP":"Php","COL":"Col","1TH":"1Th","2TH":"2Th","1TI":"1Ti","2TI":"2Ti",
"TIT":"Tit","PHM":"Phm","HEB":"Heb","JAS":"Jas","1PE":"1Pe","2PE":"2Pe","1JN":"1Jn","2JN":"2Jn",
"3JN":"3Jn","JUD":"Jud","REV":"Rev"}
strip=lambda s: re.sub(r'<[^>]+>','',s or '').strip()

modern={}
for line in open(f"{D}/modern.jsonl",encoding="utf-8"):
    m=json.loads(line); modern[m["id"]]=m

db=sqlite3.connect(DB)
db.executescript("""
DROP TABLE IF EXISTS place; DROP TABLE IF EXISTS place_verse;
CREATE TABLE place(
  place_id TEXT PRIMARY KEY, name TEXT, url_slug TEXT, types TEXT,
  status TEXT,              -- identified | disputed | unknown
  latitude REAL, longitude REAL,
  modern_name TEXT, confidence INT, vote_count INT,
  wikidata TEXT, description TEXT, thumbnail TEXT);
CREATE TABLE place_verse(
  place_id TEXT, verse_key TEXT, osis TEXT, readable TEXT,
  PRIMARY KEY(place_id, verse_key));
""")
places=[]; links=[]; unmapped=set()
for line in open(f"{D}/ancient.jsonl",encoding="utf-8"):
    a=json.loads(line)
    pid=a["id"]; name=a.get("friendly_id") or pid
    ids=a.get("identifications") or []
    best=None
    for ident in ids:
        sc=(ident.get("score") or {}).get("vote_average") or 0
        if best is None or sc > ((best.get("score") or {}).get("vote_average") or 0): best=ident
    lat=lon=None; mname=None; conf=None; votes=None; desc=None
    if best:
        desc=strip(best.get("description"))
        sc=best.get("score") or {}
        conf=sc.get("vote_average"); votes=sc.get("vote_count")
        mid=best.get("id") if best.get("id_source")=="modern" else None
        mod=modern.get(mid) if mid else None
        if mod and mod.get("lonlat"):
            ll=mod["lonlat"]
            # lonlat is a "lon,lat" STRING, longitude first.
            if isinstance(ll,str):
                parts=[x.strip() for x in ll.split(",")]
                if len(parts)>=2:
                    try: lon,lat=float(parts[0]),float(parts[1])
                    except ValueError: pass
            elif isinstance(ll,(list,tuple)) and len(ll)>=2:
                lon,lat=float(ll[0]),float(ll[1])
            mname=mod.get("friendly_id")
    # A region (Egypt, Moab) is identified but has polygon geometry rather than a
    # point, so "no coordinates" must not be reported as "location unknown".
    if lat is not None:
        status = "identified" if (conf or 0) >= 500 else "disputed"
    elif mname or (a.get("modern_associations") or {}):
        status = "region"
    else:
        status = "unknown"
    wd=None
    for v in (a.get("linked_data") or {}).values():
        i=v.get("id") if isinstance(v,dict) else None
        if isinstance(i,str) and re.fullmatch(r'Q\d+',i): wd=i; break
    th=((a.get("media") or {}).get("thumbnail") or {}).get("file")
    places.append((pid,name,a.get("url_slug"),",".join(a.get("types") or []),
                   status,lat,lon,mname,conf,votes,wd,desc,th))
    for v in a.get("verses") or []:
        usx=v.get("usx") or ""
        m=re.match(r'^([A-Z0-9]{3})\s+(\d+):(\d+)$', usx.strip())
        if not m: unmapped.add(usx); continue
        bk=USFM.get(m.group(1))
        if not bk: unmapped.add(usx); continue
        links.append((pid,f"{bk}.{m.group(2)}.{m.group(3)}",v.get("osis"),v.get("readable")))

db.executemany("INSERT OR REPLACE INTO place VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",places)
db.executemany("INSERT OR IGNORE INTO place_verse VALUES (?,?,?,?)",links)
db.executescript("""
CREATE INDEX IF NOT EXISTS ix_pv_verse ON place_verse(verse_key);
CREATE INDEX IF NOT EXISTS ix_pv_place ON place_verse(place_id);
CREATE INDEX IF NOT EXISTS ix_place_name ON place(name);
""")
db.commit()
print(f"places {len(places):,}   place-verse links {db.execute('SELECT COUNT(*) FROM place_verse').fetchone()[0]:,}")
for s,n in db.execute("SELECT status, COUNT(*) FROM place GROUP BY 1 ORDER BY 2 DESC"): print(f"  {s:12s} {n:,}")
tot=db.execute("SELECT COUNT(*) FROM place_verse").fetchone()[0]
ok=db.execute("SELECT COUNT(*) FROM place_verse pv WHERE EXISTS(SELECT 1 FROM verse v WHERE v.verse_key=pv.verse_key)").fetchone()[0]
print(f"links resolving to a canonical verse: {ok:,}/{tot:,} ({100*ok/tot:.2f}%)")
if unmapped: print("unmapped usx refs:", list(unmapped)[:6], f"({len(unmapped)} distinct)")
print(f"with coordinates: {db.execute('SELECT COUNT(*) FROM place WHERE latitude IS NOT NULL').fetchone()[0]:,}")
print(f"with wikidata:    {db.execute('SELECT COUNT(*) FROM place WHERE wikidata IS NOT NULL').fetchone()[0]:,}")
db.close()
