"""Parse TAHOT + TAGNT into canonical verse, token and morpheme tables."""
import re, os, glob, sqlite3, unicodedata

SRC = "/home/claude/bible/sources/stepbible/Translators Amalgamated OT+NT"
DB  = "/home/claude/bible/build/bible.db"

OT = "Gen Exo Lev Num Deu Jos Jdg Rut 1Sa 2Sa 1Ki 2Ki 1Ch 2Ch Ezr Neh Est Job Psa Pro Ecc Sng Isa Jer Lam Ezk Dan Hos Jol Amo Oba Jon Mic Nam Hab Zep Hag Zec Mal".split()
NT = "Mat Mrk Luk Jhn Act Rom 1Co 2Co Gal Eph Php Col 1Th 2Th 1Ti 2Ti Tit Phm Heb Jas 1Pe 2Pe 1Jn 2Jn 3Jn Jud Rev".split()
ORDER = {b: i+1 for i, b in enumerate(OT + NT)}

# Ref forms seen: Gen.1.1#01=L | Gen.31.55(32.1)#01=L | Jhn.1.1#01=NKO | Mat.1.1[1.1]#01=NKO
REF = re.compile(
    r'^(?P<bk>[1-5A-Za-z]{2,3})\.(?P<ch>\d+)\.(?P<vs>\d+)'
    r'(?P<alt>[\(\[\{][^\)\]\}]*[\)\]\}])?'
    r'#(?P<wd>\d+)(?:\.(?P<sub>\d+))?'
    r'=(?P<tt>[A-Za-z()+]+)$')

def norm(s): return unicodedata.normalize("NFC", s.strip())

def split_morph(hebrew, dstrong, grammar):
    """Hebrew line -> list of (surface, strong, morph). '/' splits prefixes/suffixes."""
    surf = [p for p in re.split(r'[/\\]', hebrew) if p.strip()]
    stro = [p for p in re.split(r'[/\\]', dstrong) if p.strip()]
    gram = [p for p in re.split(r'[/\\]', grammar) if p.strip()]
    # Only the FIRST grammar segment carries the language letter (H=Hebrew, A=Aramaic).
    # Later segments start with the part-of-speech letter, which may itself be "A"
    # (Adjective) - stripping it there corrupts the code. Normalise every segment to
    # the fully-prefixed form that TEHMC defines, e.g. "HTd", "HAamsa".
    lang = gram[0][0] if gram and gram[0] and gram[0][0] in "HA" else "H"
    out = []
    n = max(len(surf), len(stro))
    for i in range(n):
        s  = surf[i] if i < len(surf) else ""
        st = stro[i] if i < len(stro) else ""
        g  = gram[i] if i < len(gram) else ""
        if g:
            body = g[1:] if (i == 0 and g[:1] in ("H", "A")) else g
            g = lang + body
        st = st.strip().rstrip("+").strip("{}").split("=")[0]
        out.append((norm(s), st, g, lang))
    return out

def main():
    if os.path.exists(DB): os.remove(DB)
    db = sqlite3.connect(DB)
    db.executescript("""
    PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF;
    CREATE TABLE verse(
      verse_key TEXT PRIMARY KEY, book TEXT, book_order INT, chapter INT, verse INT,
      testament TEXT, alt_ref TEXT);
    CREATE TABLE token(
      token_id   TEXT PRIMARY KEY,
      verse_key  TEXT NOT NULL,
      position   INT  NOT NULL,
      subpos     INT,
      surface    TEXT,
      translit   TEXT,
      gloss      TEXT,
      alt_ref    TEXT,          -- source-tradition ref when it differs from the English key
      text_type  TEXT,          -- Heb: L/Q/K/X/R  Grk: NKO/K/N(k)O...
      editions   TEXT,          -- Greek only
      language   TEXT);
    CREATE TABLE morpheme(
      morph_id   TEXT PRIMARY KEY,
      token_id   TEXT NOT NULL,
      seq        INT  NOT NULL,
      surface    TEXT,
      strongs    TEXT,          -- extended/disambiguated, e.g. H7225G, G1722
      strongs_simple TEXT,      -- H7225 / G1722
      morph_code TEXT,
      language   TEXT);
    """)

    verses, tokens, morphs = {}, [], []
    stats = {}

    for path in sorted(glob.glob(SRC + "/TA*.txt")):
        is_heb = "TAHOT" in os.path.basename(path)
        nrows = 0
        with open(path, encoding="utf-8-sig") as fh:
            for line in fh:
                if "\t" not in line: continue
                cells = line.rstrip("\n").split("\t")
                m = REF.match(cells[0].strip())
                if not m: continue
                bk, ch, vs = m["bk"], int(m["ch"]), int(m["vs"])
                if bk not in ORDER: continue
                wd  = int(m["wd"]); sub = int(m["sub"]) if m["sub"] else None
                tt  = m["tt"]; alt = (m["alt"] or "").strip("()[]{}") or None
                vk  = f"{bk}.{ch}.{vs}"
                if vk not in verses:
                    verses[vk] = (vk, bk, ORDER[bk], ch, vs,
                                  "OT" if bk in OT else "NT", alt)
                altkey = f"[{alt}]" if alt else ""
                tid = f"{vk}{altkey}#{wd:03d}" + (f".{sub}" if sub else "") + f"@{tt}"

                if is_heb:
                    heb, trl, eng, dstr, gram = (cells[1], cells[2], cells[3], cells[4], cells[5])
                    tokens.append((tid, vk, wd, sub, norm(heb), norm(trl), eng.strip(),
                                   alt, tt, None, "H"))
                    for i, (s, st, g, lg) in enumerate(split_morph(heb, dstr, gram)):
                        if not st and not s: continue
                        simple = re.sub(r'^([HG]\d{4}).*$', r'\1', st) if st else None
                        morphs.append((f"{tid}:{i}", tid, i, s, st or None, simple, g or None, lg))
                else:
                    gk_raw, eng, strmorph, lemgloss, eds = (cells[1], cells[2], cells[3], cells[4], cells[5])
                    gm = re.match(r'^(.*?)\s*\(([^)]*)\)\s*$', gk_raw.strip())
                    surf, trl = (gm.group(1), gm.group(2)) if gm else (gk_raw.strip(), None)
                    tokens.append((tid, vk, wd, sub, norm(surf), trl, eng.strip(),
                                   alt, tt, eds.strip() or None, "G"))
                    # Crasis (e.g. kago = kai + ego) is tagged as "G1473=P-1NS + G2532=CONJ":
                    # one printed word, two lexemes. Split it into morphemes like Hebrew.
                    for i, part in enumerate(p for p in strmorph.split("+") if p.strip()):
                        st, _, mc = part.strip().partition("=")
                        st = st.strip(); mc = mc.strip()
                        simple = re.sub(r'^(G\d{4}).*$', r'\1', st) if st else None
                        morphs.append((f"{tid}:{i}", tid, i,
                                       norm(surf) if i == 0 else "",
                                       st or None, simple, mc or None, "G"))
                nrows += 1
        stats[os.path.basename(path)[:12]] = nrows

    db.executemany("INSERT INTO verse VALUES (?,?,?,?,?,?,?)", verses.values())
    db.executemany("INSERT INTO token VALUES (?,?,?,?,?,?,?,?,?,?,?)", tokens)
    db.executemany("INSERT INTO morpheme VALUES (?,?,?,?,?,?,?,?)", morphs)
    db.commit()
    for k, v in stats.items(): print(f"  {k:14s} {v:7d} rows")
    print(f"\nverses   {db.execute('SELECT COUNT(*) FROM verse').fetchone()[0]:,}")
    print(f"tokens   {db.execute('SELECT COUNT(*) FROM token').fetchone()[0]:,}")
    print(f"morphemes{db.execute('SELECT COUNT(*) FROM morpheme').fetchone()[0]:,}")
    db.close()

main()
