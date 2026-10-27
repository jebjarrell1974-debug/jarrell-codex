# -*- coding: utf-8 -*-
"""Reshape the audio index so a client can place a chapter inside its file.

Most LibriVox readings put many chapters in one file. Knowing only the
URL, a reader on Genesis 7 is dropped at Genesis 1 with half an hour of
audio and no idea where to drag to. Grouping the chapters that share a
file, in canonical order, and carrying each one's verse count lets the
player offer an estimated starting point - clearly labelled as an
estimate, because nothing here is a real timing.
"""
import io, json, os, sys, collections
SITE = '/home/claude/site/data'
# Reads the flat index build_audio.py produces on the machine with open
# internet, not the reshaped one this script writes - pass it explicitly so
# a second run cannot silently consume its own output.
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(SITE, 'audio_flat.json')
src = json.load(io.open(SRC, encoding='utf-8'))
assert 'chapters' in src and 'files' not in src, (
    SRC + ' is already reshaped; give me build_audio.py's output')
books = json.load(io.open(os.path.join(SITE, 'books.json'), encoding='utf-8'))
order = [b[0] for b in books['books']]
nch = {b[0]: b[3] for b in books['books']}

# verse counts come from the chapter shards the reader already downloads
vcount = {}
for code in order:
    for c in range(1, nch[code] + 1):
        p = os.path.join(SITE, 'ch', f'{code}.{c}.json')
        d = json.load(io.open(p, encoding='utf-8'))
        vcount[f'{code}.{c}'] = len(d['v'])
assert len(vcount) == 1189, len(vcount)

# canonical order, so a file's chapter list is in reading order
rank = {}
for bi, code in enumerate(order):
    for c in range(1, nch[code] + 1):
        rank[f'{code}.{c}'] = (bi, c)

groups = collections.OrderedDict()
for key in sorted(src['chapters'], key=lambda k: rank[k]):
    e = src['chapters'][key]
    groups.setdefault(e['url'], []).append(key)

files, chapters = [], {}
for url, keys in groups.items():
    e = src['chapters'][keys[0]]
    fi = len(files)
    files.append({
        'u': url,
        'item': e['item'],
        'mb': e['mb'],
        'ch': keys,
        'vs': [vcount[k] for k in keys],
        # A file holding exactly one of our chapters is a recording of
        # that chapter alone, whatever the source title said. Obadiah,
        # 2 John, 3 John and Jude are one-chapter books that the
        # complete-Bible set gives a file each; the title parsing read
        # those as ranges, so the 'exact' flag called them excerpts.
        'one': len(keys) == 1,
    })
    for i, k in enumerate(keys):
        chapters[k] = [fi, i]

out = {'files': files, 'chapters': chapters, 'sources': src['sources']}
dest = os.path.join(SITE, 'audio.json')
io.open(dest, 'w', encoding='utf-8').write(
    json.dumps(out, ensure_ascii=False, separators=(',', ':')))

one = sum(1 for f in files if f['one'])
print(f'files            : {len(files)}  ({one} hold a single chapter)')
print(f'chapters placed  : {len(chapters)} of 1189')
print(f'index size       : {os.path.getsize(dest)/1024:.0f} KB  (was {len(json.dumps(src))/1024:.0f} KB)')
assert len(chapters) == 1189
# every chapter must resolve to a file that actually lists it
for k, (fi, i) in chapters.items():
    assert files[fi]['ch'][i] == k, (k, fi, i)
    assert files[fi]['item'] in out['sources'], files[fi]['item']
print('every chapter resolves to a file that lists it, with a credited source')
big = max(files, key=lambda f: len(f['ch']))
print(f'largest file     : {len(big["ch"])} chapters, {big["ch"][0]} to {big["ch"][-1]}, {big["mb"]} MB')
