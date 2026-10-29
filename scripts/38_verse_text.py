# -*- coding: utf-8 -*-
"""An index of the verse text alone: one file per book, per translation.

Everywhere this reader is shown a list of verses - the concordance, the
cross-references, the places, the people, the timeline - it shows bare
references and nothing else. "Genesis 1:1, Exodus 4:2, Numbers 17:8" is
not a concordance, it is a table of contents for one, and a reader
scrolling 321 of those learns nothing.

The text is already in the chapter shards, but a shard averages 85 KB
because it carries the Hebrew, the parsing and the whole apparatus.
Fetching that to show one line is absurd.

Split per translation as well as per book, because a reader fetches only
the one they are reading. All four together are 17 MB and Psalms alone is
993 KB; one translation is 4.2 MB and the largest single file is a quarter
of that. All four still ship in the offline download, because the reader
can switch and should not then find the lists have gone quiet.
"""
import glob, io, json, os, shutil
from collections import defaultdict

DATA = '/home/claude/site/data'
OUT = os.path.join(DATA, 'vt')
shutil.rmtree(OUT, ignore_errors=True)

books = defaultdict(lambda: defaultdict(dict))   # tx -> book -> "c.v" -> text
seen = 0
for f in sorted(glob.glob(os.path.join(DATA, 'ch', '*.json'))):
    d = json.load(io.open(f, encoding='utf-8'))
    for v in d['v']:
        for code, text in (v.get('x') or {}).items():
            if text:
                books[code][d['b']][f"{d['c']}.{v['n']}"] = text
                seen += 1

per_tx = {}
for tx, bs in books.items():
    os.makedirs(os.path.join(OUT, tx), exist_ok=True)
    tot = 0
    for b, rows in bs.items():
        p = os.path.join(OUT, tx, f'{b}.json')
        io.open(p, 'w', encoding='utf-8').write(
            json.dumps(rows, ensure_ascii=False, separators=(',', ':')))
        tot += os.path.getsize(p)
    per_tx[tx] = (len(bs), tot)

print(f'{"translation":<12}{"books":>7}{"size":>10}{"largest file":>16}')
for tx, (n, tot) in sorted(per_tx.items()):
    big = max((os.path.getsize(os.path.join(OUT, tx, f)), f)
              for f in os.listdir(os.path.join(OUT, tx)))
    print(f'{tx:<12}{n:>7}{tot / 1048576:>9.1f}M'
          f'{big[1].replace(".json", ""):>10} {big[0] / 1024:>4.0f} KB')
allsize = sum(t for _, t in per_tx.values())
print(f'\nverse texts  : {seen:,}')
print(f'all together : {allsize / 1048576:.1f} MB in '
      f'{sum(n for n, _ in per_tx.values())} files')

# It has to agree with the chapter shards it came from, or a concordance
# will quote a verse that is not what the chapter actually says.
import random
random.seed(7)
checked = 0
for f in random.sample(sorted(glob.glob(os.path.join(DATA, 'ch', '*.json'))), 50):
    d = json.load(io.open(f, encoding='utf-8'))
    for code in per_tx:
        p = os.path.join(OUT, code, f"{d['b']}.json")
        rows = json.load(io.open(p, encoding='utf-8'))
        for v in d['v']:
            text = (v.get('x') or {}).get(code)
            if text:
                assert rows[f"{d['c']}.{v['n']}"] == text, (code, d['b'], v['n'])
                checked += 1
print(f'cross-checked {checked:,} verse texts against the chapter shards')
