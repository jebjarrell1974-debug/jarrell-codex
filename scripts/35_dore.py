#!/usr/bin/env python3
"""Key Gustave Dore's engravings to the verses they illustrate.

Commons records the reference in the file description rather than the
title - "The Creation of Light (Gen. 1:1-5)", "The Creation of Eve
(Gen. 1:26-27, 2:15-25)". Parsing happens here rather than on the machine
that fetched them, because this is where book_name lives and a guess at
what "Cant." or "Ecclus." means is exactly the kind of thing that should
be looked up rather than assumed.

Anything that cannot be parsed is reported, not silently dropped.
"""
import json, os, re, sqlite3, sys
from collections import defaultdict

DB   = 'build/bible.db'
SRC  = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/dore/plates.json'
OUT  = '/home/claude/site/data'

db = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)

# every spelling of every book, longest first so "1 John" beats "John"
NAMES = {}
for name, book in db.execute("SELECT name, book FROM book_name"):
    NAMES[name.lower().replace('.', '').strip()] = book
# the abbreviations an 1860s printer actually used
EXTRA = {
    'gen': 'Gen', 'exod': 'Exo', 'ex': 'Exo', 'lev': 'Lev', 'num': 'Num',
    'deut': 'Deu', 'josh': 'Jos', 'judg': 'Jdg', 'ruth': 'Rut',
    'i sam': '1Sa', 'ii sam': '2Sa', 'i kings': '1Ki', 'ii kings': '2Ki',
    'i chron': '1Ch', 'ii chron': '2Ch', 'neh': 'Neh', 'esth': 'Est',
    'ps': 'Psa', 'psa': 'Psa', 'prov': 'Pro', 'eccl': 'Ecc', 'cant': 'Sng',
    'song of sol': 'Sng', 'isa': 'Isa', 'jer': 'Jer', 'lam': 'Lam',
    'ezek': 'Ezk', 'dan': 'Dan', 'hos': 'Hos', 'joel': 'Jol', 'amos': 'Amo',
    'obad': 'Oba', 'jon': 'Jon', 'mic': 'Mic', 'nah': 'Nam', 'hab': 'Hab',
    'zeph': 'Zep', 'hag': 'Hag', 'zech': 'Zec', 'mal': 'Mal',
    'matt': 'Mat', 'mk': 'Mrk', 'mark': 'Mrk', 'lk': 'Luk', 'luke': 'Luk',
    'jn': 'Jhn', 'john': 'Jhn', 'acts': 'Act', 'rom': 'Rom',
    'i cor': '1Co', 'ii cor': '2Co', 'gal': 'Gal', 'eph': 'Eph',
    'phil': 'Php', 'col': 'Col', 'i thess': '1Th', 'ii thess': '2Th',
    'i tim': '1Ti', 'ii tim': '2Ti', 'tit': 'Tit', 'philem': 'Phm',
    'heb': 'Heb', 'jas': 'Jas', 'i pet': '1Pe', 'ii pet': '2Pe',
    'i john': '1Jn', 'ii john': '2Jn', 'iii john': '3Jn', 'jude': 'Jud',
    'rev': 'Rev',
}
for k, v in EXTRA.items():
    NAMES.setdefault(k, v)

MAXCH = {}
for b, c in db.execute("SELECT book, MAX(chapter) FROM verse GROUP BY book"):
    MAXCH[b] = c

# "Gen. 1:1-5", "Gen. 1:26-27, 2:15-25", "1 Sam. 17", "Rev. 21:1"
BOOK_RE = re.compile(r'([1-3I]{0,3}\s*[A-Za-z][A-Za-z\.]*(?:\s+of\s+\w+)?)\.?\s*'
                     r'(\d+)\s*(?::\s*(\d+)(?:\s*[-–]\s*(\d+))?)?')

# Books this 1866 set illustrates that are not in the Protestant canon we
# carry. Named so they can be reported as deliberately absent rather than
# counted as a parse failure.
APOCRYPHA = {
    'tob': 'Tobit', 'tobit': 'Tobit', 'jdth': 'Judith', 'judith': 'Judith',
    'wisd': 'Wisdom', 'ecclus': 'Ecclesiasticus', 'sirach': 'Ecclesiasticus',
    'bar': 'Baruch', 'i macc': '1 Maccabees', 'ii macc': '2 Maccabees',
    '1 macc': '1 Maccabees', '2 macc': '2 Maccabees', 'macc': 'Maccabees',
    'esdr': 'Esdras', 'sus': 'Susanna', 'bel': 'Bel and the Dragon',
}

def resolve_book(raw, chapter=None):
    """Dore's printer abbreviates Judges as "Jud.", which is also our book
    code for Jude. Jude has exactly one chapter, so any "Jud. N" with N
    above 1 is Judges. That is an inference from the data rather than a
    guess, and the chapter-range check below is what caught the collision
    in the first place - 16 plates of Samson and Gideon were being thrown
    away rather than quietly filed under a one-chapter epistle."""
    k = raw.lower().replace('.', '').strip()
    k = re.sub(r'\s+', ' ', k)
    if k in APOCRYPHA:
        return ('APOC', APOCRYPHA[k])
    if k in ('jud', 'judg', 'judges') and (chapter is None or chapter > 1):
        return 'Jdg' 
    for cand in (k, k.replace('i ', '1 ').replace('ii ', '2 ').replace('iii ', '3 ')):
        if cand in NAMES:
            return NAMES[cand]
    # longest known name that the string starts with
    for name in sorted(NAMES, key=len, reverse=True):
        if k.startswith(name):
            return NAMES[name]
    return None

def parse(desc):
    """-> (list of verse keys, the reference as printed) or (None, None)"""
    if not desc:
        return None, None
    m = re.search(r'\(([^)]*\d[^)]*)\)\s*$', desc)
    inner = m.group(1) if m else desc
    refs, book = [], None
    for mm in BOOK_RE.finditer(inner):
        raw_book, ch, v1, v2 = mm.groups()
        raw_book = raw_book.strip()
        if raw_book and not raw_book.isdigit():
            b = resolve_book(raw_book, int(ch))
            if isinstance(b, tuple):
                return 'APOCRYPHA', b[1]
            if b:
                book = b
            elif book is None:
                continue
        if book is None:
            continue
        ch = int(ch)
        if ch < 1 or ch > MAXCH.get(book, 0):
            continue
        if v1:
            a, z = int(v1), int(v2 or v1)
            refs += [f'{book}.{ch}.{v}' for v in range(a, min(z, a + 60) + 1)]
        else:
            refs.append(f'{book}.{ch}')
    return (refs or None), (m.group(1) if m else None)

plates = json.load(open(SRC, encoding='utf-8'))
print(f"plates fetched: {len(plates)}")

apocrypha = []
missing_files = []
byverse  = defaultdict(list)
bychap   = defaultdict(list)
manifest = {}
unparsed = []

for title, r in sorted(plates.items(), key=lambda kv: kv[1].get('plate') or 999):
    pid = str(r.get('plate') or len(manifest) + 1)
    parsed = parse(r.get('desc'))
    if parsed[0] == 'APOCRYPHA':
        apocrypha.append((pid, r['title'], parsed[1]))
        refs, printed = None, None
    else:
        refs, printed = parsed
    # the plates are served as WebP; the fetcher recorded the source name
    webp = os.path.splitext(r['file'])[0] + '.webp'
    on_disk = os.path.join(OUT, 'dore', webp)
    if not os.path.exists(on_disk):
        missing_files.append((pid, webp))
        continue
    manifest[pid] = {
        'file': webp, 'title': r['title'],
        'w': r.get('w'), 'h': r.get('h'),
        'ref': printed, 'page': r.get('page'),
        'licence': r.get('licence'),
    }
    if not refs:
        unparsed.append((pid, r['title'], r.get('desc')))
        continue
    seen = set()
    for key in refs:
        if key in seen:
            continue
        seen.add(key)
        parts = key.split('.')
        if len(parts) == 3:
            # only keep a verse that exists
            if db.execute("SELECT 1 FROM verse WHERE verse_key=?", (key,)).fetchone():
                byverse[key].append(pid)
            bychap[f'{parts[0]}.{parts[1]}'].append(pid)
        else:
            bychap[key].append(pid)

for k in bychap:
    out, seen = [], set()
    for p in bychap[k]:
        if p not in seen:
            seen.add(p); out.append(p)
    bychap[k] = out

os.makedirs(OUT, exist_ok=True)
# A plate is shown once, at the first verse it illustrates, rather than
# repeated under every verse of the passage it covers.
firstverse = {}
for vk in sorted(byverse, key=lambda k: (k.split('.')[0], int(k.split('.')[1]),
                                         int(k.split('.')[2]))):
    for pid in byverse[vk]:
        firstverse.setdefault(pid, vk)
at = defaultdict(list)
for pid, vk in firstverse.items():
    at[vk].append(pid)

with open(f'{OUT}/dore.json', 'w', encoding='utf-8') as f:
    json.dump({'plates': manifest, 'at': at, 'bychapter': bychap},
              f, ensure_ascii=False, separators=(',', ':'))

print(f"plates shown at    : {len(at):,} verses (each plate once)")
print(f"keyed to a verse   : {len(byverse):,} verses")
print(f"keyed to a chapter : {len(bychap):,} chapters")
print(f"plates placed      : {len(manifest) - len(unparsed)} of {len(manifest)}")
print(f"index: {os.path.getsize(f'{OUT}/dore.json')/1024:.0f} KB")
if missing_files:
    print(f"\nMISSING IMAGE FILES ({len(missing_files)}):")
    for pid, fn in missing_files[:10]:
        print(f"   {pid}  {fn}")
if apocrypha:
    print(f"\n{len(apocrypha)} plates illustrate books this Bible does not carry:")
    for pid, t, bk in apocrypha[:14]:
        print(f"   {pid:>4}  {t[:44]:<44} {bk}")
if unparsed:
    print(f"\ncould not place {len(unparsed)} - Commons records no reference:")
    for pid, t, d in unparsed[:25]:
        print(f"   {pid:>4}  {t[:46]:<46} {str(d)[:40]}")
