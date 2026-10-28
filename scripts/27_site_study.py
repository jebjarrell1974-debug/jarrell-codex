#!/usr/bin/env python3
"""Export the study layers the reader needs: concordance, gazetteer,
people, events, dictionary, and a chronological reading order."""
import json, os, re, sqlite3, sys
from collections import defaultdict

DB   = 'build/bible.db'
OUT  = '/home/claude/site/data'
CAP  = 1500          # refs kept per headword; total count always reported

def w(path, obj):
    full = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, separators=(',', ':'))
    return os.path.getsize(full)

def bucket(s):
    """H0559 -> H05 ; G26 -> G00 ; keeps shards ~100 per language."""
    m = re.match(r'^([HGA])(\d+)', s)
    if not m: return 'XX'
    return m.group(1) + m.group(2).zfill(4)[:2]

c = sqlite3.connect(DB)
c.row_factory = sqlite3.Row
report = {}

# Every verse list goes out in Bible order. Sorting on verse_key is
# alphabetical, which puts 1 Chronicles before Genesis and 15:25 before 15:3,
# and because the lists are capped it also decided WHICH verses survived:
# Jerusalem kept 400 of 955, every one of them from a book whose code sorts
# early, and not one from Genesis. Sort first, then cap.
VORD = {r[0]: (r[1], r[2], r[3]) for r in c.execute(
    "select verse_key, book_order, chapter, verse from verse")}
def canon(refs):
    return sorted(refs, key=lambda vk: VORD.get(vk, (999, 0, 0)))

# ---------------------------------------------------------------- concordance
print('concordance...', flush=True)
occ = defaultdict(list)
q = """select m.strongs_simple ss, t.verse_key vk
       from morpheme m join token t on t.token_id = m.token_id
       where m.strongs_simple is not null and m.strongs_simple <> ''
       order by t.verse_key"""
seen = set()
for ss, vk in c.execute(q):
    k = (ss, vk)
    if k in seen: continue      # one hit per verse per headword
    seen.add(k)
    occ[ss].append(vk)
del seen

shards = defaultdict(dict)
truncated = 0
for ss, refs in occ.items():
    refs = canon(refs)
    n = len(refs)
    if n > CAP:
        truncated += 1
        refs = refs[:CAP]
    shards[bucket(ss)][ss] = [n, refs]

tot = 0
for b, payload in shards.items():
    tot += w(f'conc/{b}.json', payload)
report['concordance'] = dict(headwords=len(occ), shards=len(shards),
                             truncated=truncated, mb=round(tot/1048576, 1))
print(f"  {len(occ)} headwords, {len(shards)} shards, {tot/1048576:.1f} MB"
      f" ({truncated} capped at {CAP})", flush=True)

# ------------------------------------------------------------------ gazetteer
print('places...', flush=True)
pv = defaultdict(list)
for r in c.execute("select place_id, verse_key from place_verse order by verse_key"):
    pv[r['place_id']].append(r['verse_key'])
places = {}
for r in c.execute("select * from place"):
    refs = canon(pv.get(r['place_id'], []))
    places[r['name']] = {
        'slug':   r['url_slug'],
        'status': r['status'],
        'lat':    r['latitude'],
        'lon':    r['longitude'],
        'modern': r['modern_name'],
        'types':  r['types'],
        'conf':   r['confidence'],
        'votes':  r['vote_count'],
        'wd':     r['wikidata'],
        'desc':   r['description'],
        'n':      len(refs),
        'refs':   refs[:400],
    }
report['places'] = dict(n=len(places), mb=round(w('place.json', places)/1048576, 2))
print(f"  {len(places)} places", flush=True)

# --------------------------------------------------------------------- people
print('people...', flush=True)
sv = defaultdict(list)
for r in c.execute("select person_id, verse_key from person_verse order by verse_key"):
    sv[r['person_id']].append(r['verse_key'])
people = {}
dupes = 0
for r in c.execute("select * from person order by person_id"):
    refs = canon(sv.get(r['person_id'], []))
    rec = {
        'title':  r['display_title'],
        'slug':   r['slug'],
        'sex':    r['gender'],
        'born':   r['birth_year'],
        'died':   r['death_year'],
        'n':      len(refs),
        'refs':   refs[:400],
    }
    name = r['name']
    if name in people:
        # Theographic carries several distinct people under one name
        # (four men called Azariah, and so on). Keep them as numbered
        # senses instead of letting the last one win.
        dupes += 1
        people[name].setdefault('also', []).append(rec)
    else:
        people[name] = rec
report['people'] = dict(n=len(people), senses=len(people)+dupes, mb=round(w('person.json', people)/1048576, 2))
print(f"  {len(people)} names, {dupes} extra senses merged", flush=True)

# --------------------------------------------------------------------- events
print('events...', flush=True)
ev_v = defaultdict(list)
for r in c.execute("select event_id, verse_key from event_verse order by verse_key"):
    ev_v[r['event_id']].append(r['verse_key'])
ev_d = defaultdict(dict)
for r in c.execute("select * from event_date"):
    ev_d[r['event_id']][r['scheme_id']] = [r['start_year'], r['end_year'],
                                           r['precision'], r['note']]
events = {}
for r in c.execute("select * from event order by sort_key"):
    eid = str(r['event_id'])
    events[eid] = {
        'title': r['title'],
        'sort':  r['sort_key'],
        'dur':   r['duration'],
        'dates': ev_d.get(r['event_id'], {}),
        'refs':  canon(ev_v.get(r['event_id'], [])),
    }
report['events'] = dict(n=len(events), mb=round(w('event.json', events)/1048576, 2))
print(f"  {len(events)} events", flush=True)

# ----------------------------------------------------------------- dictionary
print('dictionary...', flush=True)
dsh = defaultdict(dict)
index = {}
for r in c.execute("select * from dictionary order by term_label, item_num"):
    label = r['term_label']
    key   = (r['lookup'] or label).strip().lower()
    b     = re.sub(r'[^a-z]', '', key[:1]) or 'other'
    eid   = str(r['entry_id'])
    dsh[b][eid] = {'label': label, 'body': r['body'],
                   'num': r['item_num'], 'src': r['source'],
                   'person': r['person_slug']}
    index.setdefault(key, []).append([eid, b, label, r['item_num']])
tot = sum(w(f'dict/{b}.json', payload) for b, payload in dsh.items())
tot += w('dict_index.json', index)
report['dictionary'] = dict(entries=sum(len(v) for v in dsh.values()),
                            headwords=len(index), shards=len(dsh),
                            mb=round(tot/1048576, 2))
print(f"  {sum(len(v) for v in dsh.values())} entries under {len(index)} headwords", flush=True)

# --------------------------------------------- chronological reading order
print('chronological order...', flush=True)
BOOK_ORD = {r['code']: i for i, r in enumerate(
    c.execute("select distinct book code from verse order by rowid"))}
books = [r[0] for r in c.execute(
    "select book, min(rowid) from verse group by book order by min(rowid)")]
BOOK_ORD = {b: i for i, b in enumerate(books)}

def ref_sort(vk):
    p = vk.split('.')
    return (BOOK_ORD.get(p[0], 999), int(p[1]) if len(p) > 1 and p[1].isdigit() else 0,
            int(p[2]) if len(p) > 2 and p[2].isdigit() else 0)

def span(refs):
    """Collapse a verse list into readable passage spans."""
    if not refs: return []
    rs = sorted(set(refs), key=ref_sort)
    out, cur = [], None
    for vk in rs:
        b, ch, v = (vk.split('.') + ['0', '0'])[:3]
        ch, v = int(ch) if ch.isdigit() else 0, int(v) if v.isdigit() else 0
        if cur and cur[0] == b and cur[1] == ch and v == cur[3] + 1:
            cur[3] = v
        else:
            if cur: out.append(cur)
            cur = [b, ch, v, v]
        if len(out) > 40: break
    if cur: out.append(cur)
    return out

schemes = [r['scheme_id'] for r in c.execute(
    "select scheme_id from chronology_scheme order by is_default desc, scheme_id")]
order = {}
for s in schemes:
    rows = []
    for eid, e in events.items():
        d = e['dates'].get(s)
        y = d[0] if d else None
        rows.append((y, e['sort'], eid))
    dated   = sorted([r for r in rows if r[0] is not None], key=lambda r: (r[0], r[1] or 0))
    undated = sorted([r for r in rows if r[0] is None], key=lambda r: (r[1] or 0))
    order[s] = dict(dated=[r[2] for r in dated], undated=[r[2] for r in undated])

spans = {eid: span(e['refs']) for eid, e in events.items()}
notes = [dict(heading=r['heading'], body=r['body'])
         for r in c.execute("select * from chronology_note order by sort_order")]
sz = w('chrono_order.json', dict(order=order, spans=spans, notes=notes,
                                 schemes=schemes))
report['chronology'] = dict(schemes=len(schemes),
                            dated={s: len(v['dated']) for s, v in order.items()},
                            mb=round(sz/1048576, 2))
for s, v in order.items():
    print(f"  {s:<11} {len(v['dated']):>3} dated / {len(v['undated']):>3} undated", flush=True)

w('study_report.json', report)
print()
print(json.dumps(report, indent=2))
