#!/usr/bin/env python3
"""Import six public-domain commentaries and key them to our chapters.

Only sources whose terms are unambiguous are taken. The Early Church
Fathers module is deliberately left out: its English translations are
described as "19th-century and later", and "and later" is a copyright
question that cannot be settled per author. This Bible is meant to be
copied and handed out, so anything whose terms we cannot stand behind
does not go in it.
"""
import json, os, re, sqlite3, sys
from collections import defaultdict

EXT  = '/home/claude/extern/sdj'
OUT  = '/home/claude/site/data'
DB   = 'build/bible.db'

SOURCES = [
    ('henry',    'Matthew Henry',            'Commentary on the Whole Bible, 1708–1710'),
    ('geneva',   'Geneva Bible notes',       'Marginal notes of the 1599 Geneva Bible'),
    ('calvin',   'John Calvin',              'Commentaries, Calvin Translation Society, 1840s–50s'),
    ('poole',    'Matthew Poole',            'English Annotations on the Holy Bible, 1683–1685'),
    ('trapp',    'John Trapp',               'A Commentary upon All the Books, 1647–1656'),
    ('spurgeon', 'C. H. Spurgeon',           'The Treasury of David, 1869–1885 (Psalms)'),
]

c = sqlite3.connect(DB)
BOOKS = {b.upper(): b for (b,) in c.execute(
    "select distinct book from verse")}
CHAPS = defaultdict(int)
for b, ch in c.execute("select book, max(chapter) from verse group by book"):
    CHAPS[b] = ch

def parse_range(r):
    """'JHN'       -> (1, None, None, True)   a preface to the whole book
       'JHN.3'     -> (3, None, None, False)
       'JHN.3.16'  -> (3, 16, 16, False)
       'JHN.3.1-21'-> (3, 1, 21, False)"""
    r = (r or '').strip()
    if re.match(r'^[A-Z0-9]+$', r):
        return (1, None, None, True)          # hang it on chapter 1
    m = re.match(r'^([A-Z0-9]+)\.(\d+)(?:\.(\d+)(?:-(\d+))?)?$', r)
    if not m: return None
    _, ch, v1, v2 = m.groups()
    if v1 is None: return (int(ch), None, None, False)
    return (int(ch), int(v1), int(v2 or v1), False)

out = defaultdict(lambda: defaultdict(list))   # book -> chapter -> units
stats = defaultdict(lambda: [0, 0])            # src -> [units, paragraphs]
skipped_ranges = defaultdict(int)

for sid, author, work in SOURCES:
    root = f'{EXT}/en/{sid}'
    if not os.path.isdir(root):
        print(f"  {sid}: not present, skipped"); continue
    for up in sorted(os.listdir(root)):
        book = BOOKS.get(up)
        if not book:
            if up.endswith('.md'): continue
            skipped_ranges[f'{sid}:book:{up}'] += 1
            continue
        for fn in sorted(os.listdir(f'{root}/{up}')):
            if not fn.endswith('.json'): continue
            try:
                d = json.load(open(f'{root}/{up}/{fn}', encoding='utf-8'))
            except Exception:
                skipped_ranges[f'{sid}:unreadable'] += 1; continue
            for u in d.get('units', []):
                pr = parse_range(u.get('range'))
                if not pr:
                    skipped_ranges[f'{sid}:range:{u.get("range")!r}'] += 1; continue
                ch, v1, v2, is_book = pr
                if ch < 1 or ch > CHAPS.get(book, 0):
                    skipped_ranges[f'{sid}:chapter-out-of-range'] += 1; continue
                paras = [p.get('text', '').strip()
                         for p in u.get('paragraphs', []) if p.get('text', '').strip()]
                if not paras: continue
                # [source, kind, title, firstVerse, lastVerse, paragraphs]
                out[book][ch].append(
                    [sid, 'book' if is_book else (u.get('kind') or 'passage'),
                     u.get('title') or None, v1, v2, paras])
                stats[sid][0] += 1
                stats[sid][1] += len(paras)

srcmeta = {sid: [author, work] for sid, author, work in SOURCES}
ORDER = {sid: i for i, (sid, _, _) in enumerate(SOURCES)}

total = files = 0
index = {}
for book, chs in out.items():
    for ch, units in chs.items():
        # chapter-wide first, then by verse, then by source order
        # book prefaces, then chapter-wide, then by verse, then by source order
        units.sort(key=lambda u: (0 if u[1] == 'book' else 1,
                                  u[3] is not None, u[3] or 0, u[4] or 0,
                                  ORDER.get(u[0], 99)))
        p = f'{OUT}/cm/{book}.{ch}.json'
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8') as f:
            json.dump({'b': book, 'c': ch, 'u': units}, f,
                      ensure_ascii=False, separators=(',', ':'))
        total += os.path.getsize(p); files += 1
        index[f'{book}.{ch}'] = len(units)

with open(f'{OUT}/commentary.json', 'w', encoding='utf-8') as f:
    json.dump({'sources': srcmeta, 'order': [s for s, _, _ in SOURCES],
               'chapters': index}, f, ensure_ascii=False, separators=(',', ':'))

print(f"\n{'source':<10} {'units':>8} {'paragraphs':>12}")
for sid, _, _ in SOURCES:
    u, p = stats[sid]
    print(f"{sid:<10} {u:>8,} {p:>12,}")
print(f"\nchapters with commentary: {files:,} of {sum(CHAPS.values()):,}")
print(f"commentary data: {total/1048576:.1f} MB")
if skipped_ranges:
    print("\nskipped:")
    for k, v in sorted(skipped_ranges.items()): print(f"  {k}: {v}")
