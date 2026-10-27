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
    # The printer also writes the Kingdoms and Chronicles in the singular,
    # and uses arabic numerals as readily as roman: "2 King 25:1-7".
    '1 king': '1Ki', '2 king': '2Ki', 'i king': '1Ki', 'ii king': '2Ki',
    '1 kings': '1Ki', '2 kings': '2Ki',
    '1 chron': '1Ch', '2 chron': '2Ch', '1 chronicle': '1Ch',
    '2 chronicle': '2Ch', '1 sam': '1Sa', '2 sam': '2Sa',
    '1 samuel': '1Sa', '2 samuel': '2Sa', '1 cor': '1Co', '2 cor': '2Co',
    '1 thess': '1Th', '2 thess': '2Th', '1 tim': '1Ti', '2 tim': '2Ti',
    '1 pet': '1Pe', '2 pet': '2Pe', '1 john': '1Jn', '2 john': '2Jn',
    '3 john': '3Jn',
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

# Two of the Maccabees plates have their reference typed in Cyrillic -
# "2 \u041cacc. 9:1-9" with a Cyrillic \u041c, "2 \u041c\u0430\u0441\u0441. 6:18-31" with three. They
# look exactly like Latin and match nothing. Folding the lookalikes back is
# a transliteration, not a guess.
CYR = str.maketrans({
    '\u0410': 'A', '\u0412': 'B', '\u0415': 'E', '\u041a': 'K', '\u041c': 'M', '\u041d': 'H', '\u041e': 'O',
    '\u0420': 'P', '\u0421': 'C', '\u0422': 'T', '\u0425': 'X', '\u0430': 'a', '\u0432': 'b', '\u0435': 'e',
    '\u043a': 'k', '\u043c': 'm', '\u043d': 'h', '\u043e': 'o', '\u0440': 'p', '\u0441': 'c', '\u0443': 'y',
    '\u0445': 'x', '\u0456': 'i',
})


def resolve_book(raw, chapter=None):
    """Dore's printer abbreviates Judges as "Jud.", which is also our book
    code for Jude. Jude has exactly one chapter, so any "Jud. N" with N
    above 1 is Judges. That is an inference from the data rather than a
    guess, and the chapter-range check below is what caught the collision
    in the first place - 16 plates of Samson and Gideon were being thrown
    away rather than quietly filed under a one-chapter epistle."""
    k = raw.translate(CYR).lower().replace('.', '').strip()
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
    # An abbreviation that is a prefix of several books: "Ez." could be Ezra
    # or Ezekiel. If only one of the candidates HAS the chapter printed on
    # the plate, that is the one - Ezra stops at ten, so "Ez. 14" is Ezekiel.
    # An inference from the data, like the Judges/Jude case above.
    if chapter is not None and len(k) >= 2:
        fits = {NAMES[n] for n in NAMES
                if n.startswith(k) and chapter <= MAXCH.get(NAMES[n], 0)}
        if len(fits) == 1:
            return fits.pop()
    return None

def parse(desc):
    """-> (list of verse keys, the reference as printed) or (None, None)"""
    if not desc:
        return None, None
    # Fold the Cyrillic lookalikes before the regex runs, not after. The
    # book pattern needs [A-Za-z] for its first letter, so "2 \u041c\u0430\u0441\u0441." never
    # reached resolve_book to be folded there at all.
    desc = desc.translate(CYR)
    m = re.search(r'\(([^)]*\d[^)]*)\)\s*$', desc)
    inner = m.group(1) if m else desc
    refs, book, chap, beyond = [], None, None, set()
    BARE = re.compile(r'^\s*(?:(\d+)\s*:\s*)?(\d+)(?:\s*[-\u2013]\s*(\d+))?\s*$')
    for piece in re.split(r'[;,]', inner):
        if not piece.strip():
            continue
        mm = BOOK_RE.search(piece)
        if mm:
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
            chap = int(ch)
            v_from, v_to = v1, v2
        else:
            # no book letter here: a continuation of the last one
            bm = BARE.match(piece)
            if not bm or book is None:
                continue
            c, a, z = bm.groups()
            if c:
                chap, v_from, v_to = int(c), a, z
            elif chap is not None:
                v_from, v_to = a, z
            else:
                chap, v_from, v_to = int(a), None, None
        if book is None or chap is None:
            continue
        if chap < 1 or chap > MAXCH.get(book, 0):
            beyond.add(f'{book} {chap}')
            continue
        if v_from:
            a, z = int(v_from), int(v_to or v_from)
            refs += [f'{book}.{chap}.{v}' for v in range(a, min(z, a + 60) + 1)]
        else:
            refs.append(f'{book}.{chap}')
    printed = m.group(1) if m else None
    if not refs and beyond:
        return ('BEYOND', sorted(beyond))
    return (refs or None), printed

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
    elif parsed[0] == 'BEYOND':
        # e.g. "Dan. 13:1-26": a real book, a chapter it does not have.
        apocrypha.append((pid, r['title'],
                          ' and '.join(parsed[1]) + ', which this Bible does not have'))
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

apoc = {pid: bk for pid, _t, bk in apocrypha if pid in manifest}

# One plate carries no reference at all but sits in the middle of the run
# that illustrates the Apocrypha: 112 "Judith and Holofernes" between 111
# (Tobit) and 113 (Judith). The plates are numbered in canonical order
# throughout the set, so a gap whose nearest neighbours on BOTH sides are
# outside this Bible is outside it too. That is the plate ordering talking,
# not the title - the five Genesis plates with no reference have Genesis
# neighbours and stay where they are, unplaced and said to be.
order = sorted(manifest, key=lambda k: int(k))
shown = {pid for pids in at.values() for pid in pids}
bracketed = 0
for i, pid in enumerate(order):
    if pid in shown or pid in apoc:
        continue
    before = next((order[j] for j in range(i - 1, -1, -1)
                   if order[j] in shown or order[j] in apoc), None)
    after = next((order[j] for j in range(i + 1, len(order))
                  if order[j] in shown or order[j] in apoc), None)
    if before in apoc and after in apoc:
        apoc[pid] = ('the same part of the set as the plates either side, '
                     'which this Bible does not carry')
        bracketed += 1
if bracketed:
    print(f"\n{bracketed} plate(s) placed outside this Bible by the plate order alone")
with open(f'{OUT}/dore.json', 'w', encoding='utf-8') as f:
    json.dump({'plates': manifest, 'at': at, 'bychapter': bychap,
               'apoc': apoc},
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
