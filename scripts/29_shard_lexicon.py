#!/usr/bin/env python3
"""Split lexicon.json into per-prefix shards so a word tap fetches ~30 KB
instead of 13.8 MB. Same shard key as the concordance."""
import json, os, re
OUT = '/home/claude/site/data'
src = json.load(open(f'{OUT}/lexicon.json', encoding='utf-8'))

def bucket(s):
    m = re.match(r'^([HGA])(\d+)', s)
    return m.group(1) + m.group(2).zfill(4)[:2] if m else 'XX'

sh = {}
for k, v in src.items():
    sh.setdefault(bucket(k), {})[k] = v

tot = 0
for b, payload in sh.items():
    p = f'{OUT}/lex/{b}.json'
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, separators=(',', ':'))
    tot += os.path.getsize(p)

big = max(os.path.getsize(f'{OUT}/lex/{b}.json') for b in sh)
os.remove(f'{OUT}/lexicon.json')
print(f"{len(src)} entries -> {len(sh)} shards, {tot/1048576:.1f} MB total, "
      f"largest shard {big/1024:.0f} KB")
