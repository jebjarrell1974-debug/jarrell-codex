#!/usr/bin/env python3
"""Sharded inverted index so the static reader can search without a server.

Three indexes:
  idx/w/<shard>.json   KJV word -> verse refs        (verse text search)
  idx/g/<shard>.json   gloss word -> Strong's        (English -> original word)
  idx/n/<shard>.json   note word -> verse refs       (commentary search)
Shard key is the first two letters of the term, so the client fetches
exactly one small file per query word.
"""
import json, os, re, sqlite3
from collections import defaultdict

DB, OUT = 'build/bible.db', '/home/claude/site/data'
CAP = 2000

STOP = set("""a an the and or but if of in on at to for with from by as is are was were
be been being this that these those it its he she they them his her their you your
i me my we us our not no so then than there here which who whom whose what when
where how all any both each few more most other some such only own same too very
s t can will just don should now shall unto thou thee thy ye hath doth""".split())

def norm(t):
    return re.sub(r"[^a-z']", '', t.lower()).strip("'")

def shard(term):
    k = re.sub(r"[^a-z]", '', term[:2])
    return (k + 'zz')[:2] if k else 'xx'

def write_index(name, table, label):
    tot = files = 0
    for s, payload in table.items():
        p = f'{OUT}/idx/{name}/{s}.json'
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, separators=(',', ':'))
        tot += os.path.getsize(p); files += 1
    terms = sum(len(v) for v in table.values())
    print(f"  {label:<22} {terms:>7} terms  {files:>4} shards  {tot/1048576:>6.1f} MB", flush=True)
    return dict(terms=terms, shards=files, mb=round(tot/1048576, 1))

c = sqlite3.connect(DB)
c.row_factory = sqlite3.Row
rep = {}

# ----------------------------------------------------- verse text (KJV)
print('verse text index (KJV)...', flush=True)
words = defaultdict(set)
rows = c.execute("""select canonical_key k, text t from translation_verse
                    where code = 'KJV' and canonical_key is not null""")
for k, txt in rows:
    for tok in set(norm(x) for x in txt.split()):
        if len(tok) > 1 and tok not in STOP:
            words[tok].add(k)
tbl = defaultdict(dict)
cap = 0
for term, refs in words.items():
    r = sorted(refs)
    if len(r) > CAP: cap += 1
    tbl[shard(term)][term] = [len(r), r[:CAP]]
rep['verse'] = write_index('w', tbl, 'KJV words')
rep['verse']['capped'] = cap
del words, tbl

# -------------------------------------------- English gloss -> Strong's
print('gloss index...', flush=True)
gl = defaultdict(lambda: defaultdict(int))
for strongs, gloss in c.execute(
        """select m.strongs_simple, t.gloss
           from morpheme m join token t on t.token_id = m.token_id
           where m.strongs_simple is not null and t.gloss is not null"""):
    for tok in set(norm(x) for x in re.split(r'[\s/|]+', gloss)):
        if len(tok) > 1 and tok not in STOP:
            gl[tok][strongs] += 1
tbl = defaultdict(dict)
for term, hits in gl.items():
    top = sorted(hits.items(), key=lambda kv: -kv[1])[:40]
    tbl[shard(term)][term] = top
rep['gloss'] = write_index('g', tbl, 'gloss words')
del gl, tbl

# ----------------------------------------------- translation notes text
print('note index...', flush=True)
nw = defaultdict(set)
for k, body in c.execute("select verse_key, body from note where body is not null and verse_key is not null"):
    plain = re.sub(r'[*_\[\]()#>]', ' ', body)
    for tok in set(norm(x) for x in plain.split()):
        if len(tok) > 2 and tok not in STOP:
            nw[tok].add(k)
tbl = defaultdict(dict)
cap = 0
for term, refs in nw.items():
    r = sorted(refs)
    if len(r) > CAP: cap += 1
    tbl[shard(term)][term] = [len(r), r[:CAP]]
rep['note'] = write_index('n', tbl, 'note words')
rep['note']['capped'] = cap

with open(f'{OUT}/search_report.json', 'w') as f:
    json.dump(rep, f, indent=2)
print()
print(json.dumps(rep, indent=2))
