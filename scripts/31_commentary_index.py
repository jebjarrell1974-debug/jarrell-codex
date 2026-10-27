#!/usr/bin/env python3
"""Fold a commentary count into each verse of the chapter files.

The commentary itself is 86 KB for a median chapter and 2 MB for Psalm 119,
so it is fetched only when asked for. But the reader has to know whether to
offer it before the reader taps. One integer per verse, in a file already
being fetched, costs nothing and answers that.
"""
import json, os, glob
OUT = '/home/claude/site/data'

chapters = sorted(glob.glob(f'{OUT}/cm/*.json'))
touched = verses = chapter_level = 0
missing = []

for cp in chapters:
    key = os.path.basename(cp)[:-5]                 # Jhn.3
    vp  = f'{OUT}/ch/{key}.json'
    if not os.path.exists(vp):
        missing.append(key); continue
    cm = json.load(open(cp, encoding='utf-8'))
    per, wide = {}, 0
    for u in cm['u']:
        _, kind, _, v1, v2, paras = u
        if v1 is None:                              # book preface or whole chapter
            wide += 1
            continue
        for v in range(v1, (v2 or v1) + 1):
            per[v] = per.get(v, 0) + 1
    d = json.load(open(vp, encoding='utf-8'))
    for v in d['v']:
        n = per.get(v['n'], 0)
        if n: v['cm'] = n; verses += 1
        else: v.pop('cm', None)
    if wide: d['cmc'] = wide
    else: d.pop('cmc', None)
    chapter_level += wide
    with open(vp, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, separators=(',', ':'))
    touched += 1

print(f"chapters updated:        {touched:,}")
print(f"verses with commentary:  {verses:,}")
print(f"chapter/book-wide units: {chapter_level:,}")
if missing: print(f"NO CHAPTER FILE for:     {missing}")
