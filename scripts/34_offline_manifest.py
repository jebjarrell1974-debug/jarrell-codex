#!/usr/bin/env python3
"""List every published file in tiers, so the reader can take it all offline.

Caching only the chapters somebody happens to open is no use to a person
who is about to lose signal for a week. This lets them pull the lot down
on wifi first, and choose how much of it they want to carry.
"""
import json, os

SITE = '/home/claude/site'
DATA = f'{SITE}/data'

def walk(sub, pred=lambda p: True):
    out = []
    root = os.path.join(DATA, sub) if sub else DATA
    for dirpath, _, files in os.walk(root):
        for fn in sorted(files):
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, SITE).replace(os.sep, '/')
            if pred(rel):
                out.append([rel, os.path.getsize(p)])
    return sorted(out)

tiers = {}

# Tier 1 - the Bible itself: every chapter, with its parsing, translations,
# places, people, events, notes and cross-references already inside.
tiers['text'] = {
    'label': 'The text',
    'note': 'Every chapter: the original languages with every word parsed, '
            'four English translations, the places, the people, the events, '
            'the translators’ notes and the cross-references.',
    'files': walk('ch'),
}

# Tier 2 - what a word tap needs.
study = walk('lex') + walk('conc') + [
    [f'data/{f}', os.path.getsize(f'{DATA}/{f}')]
    for f in ('morph.json', 'place.json', 'person.json', 'event.json',
              'chronology.json', 'chrono_order.json', 'dict_index.json')
    if os.path.exists(f'{DATA}/{f}')
] + walk('dict')
tiers['study'] = {
    'label': 'Word study',
    'note': 'The lexicons, the concordance, the Bible dictionary, the '
            'gazetteer and the chronologies — everything behind tapping '
            'a word or a marker.',
    'files': sorted(study),
}

tiers['search'] = {
    'label': 'Search',
    'note': 'The indexes that let you search the text, the glosses and the '
            'notes with no connection.',
    'files': walk('idx'),
}

pix = walk('pix')
if os.path.exists(f'{DATA}/pix_manifest.json'):
    pix.append(['data/pix_manifest.json', os.path.getsize(f'{DATA}/pix_manifest.json')])
tiers['pictures'] = {
    'label': 'Photographs of the places',
    'note': 'A photograph of each biblical site that has one \u2014 307 of the '
            '1,342 places. The rest have no picture, and say so.',
    'files': sorted(pix),
}

dore = walk('dore')
if os.path.exists(f'{DATA}/dore.json'):
    dore.append(['data/dore.json', os.path.getsize(f'{DATA}/dore.json')])
if dore:
    tiers['engravings'] = {
        'label': 'Dor\u00e9\u2019s engravings',
        'note': '150 plates engraved for the Bible in 1866, set in the text '
                'at the verse each one illustrates.',
        'files': sorted(dore),
    }

tiers['commentary'] = {
    'label': 'The commentators',
    'note': 'Henry, the Geneva notes, Calvin, Poole, Trapp and Spurgeon on '
            'almost every verse. The biggest piece by far — skip it if '
            'you are short of room.',
    'files': walk('cm'),
}

report = {}
for k, t in tiers.items():
    total = sum(sz for _, sz in t['files'])
    t['bytes'] = total
    t['count'] = len(t['files'])
    report[k] = (len(t['files']), total)

out = {'tiers': tiers}
p = f'{DATA}/offline_manifest.json'
with open(p, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, separators=(',', ':'))

print(f"{'tier':<12} {'files':>7} {'size':>10}")
grand = 0
for k, (n, b) in report.items():
    print(f"{k:<12} {n:>7,} {b/1048576:>9.1f} MB")
    grand += b
print(f"{'TOTAL':<12} {sum(n for n,_ in report.values()):>7,} {grand/1048576:>9.1f} MB")
print(f"\nmanifest itself: {os.path.getsize(p)/1024:.0f} KB")
