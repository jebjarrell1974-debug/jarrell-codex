# -*- coding: utf-8 -*-
"""Second pass: fall back to the uploader, which is what Commons itself does.

The first pass asked for the Artist field and got five of fourteen. Nine
files have no Artist template at all, and one says "Own work", which is not
a name. For those, Commons' own attribution generator credits the account
that uploaded the file, so that is what goes in - with the username as the
username, not dressed up as a person's name.
"""
import io, json, os, re, sys, time, urllib.parse, urllib.request

GHP = r'C:\Android\work\ghp3'
MAN = os.path.join(GHP, 'data', 'pix_manifest.json')
API = 'https://commons.wikimedia.org/w/api.php'
UA = ('jarrell-codex/1.0 (attribution fixup; '
      'https://github.com/jebjarrell1974-debug/jarrell-codex)')

# Things the Artist field says that are not a name.
NOT_A_NAME = {'own work', 'unknown', 'unknown author', 'anonymous',
              'see below', 'no machine-readable author provided',
              'not provided', '-', ''}


def txt(o, k):
    v = o.get(k)
    return v if isinstance(v, str) else ''


def title_of(page):
    m = re.search(r'/wiki/(.+)$', page or '')
    return urllib.parse.unquote(m.group(1)).replace('_', ' ') if m else None


def ask(titles):
    q = urllib.parse.urlencode({
        'action': 'query', 'format': 'json', 'prop': 'imageinfo',
        'iiprop': 'user|extmetadata', 'titles': '|'.join(titles),
        'iiextmetadatafilter': 'Artist|Attribution|Credit',
    })
    r = urllib.request.Request(API + '?' + q, headers={'User-Agent': UA})
    with urllib.request.urlopen(r, timeout=60) as h:
        return json.load(h)


man = json.load(io.open(MAN, encoding='utf-8'))

need = []
for name, o in man.items():
    a = txt(o, 'artist').strip()
    lic = (txt(o, 'licence') + ' ' + txt(o, 'licurl')).lower()
    public = ('publicdomain' in lic or 'public domain' in lic or 'cc0' in lic)
    if public:
        continue
    if a and a.lower() not in NOT_A_NAME:
        continue
    t = title_of(txt(o, 'page'))
    if t:
        need.append((name, t))
    else:
        print(f'  no commons page for {name}')

print(f'{len(need)} still need a credit')
found = {}
for i in range(0, len(need), 20):
    data = ask([t for _, t in need[i:i + 20]])
    for pg in (data.get('query', {}).get('pages', {}) or {}).values():
        t = pg.get('title', '')
        ii = (pg.get('imageinfo') or [{}])[0]
        user = (ii.get('user') or '').strip()
        if user:
            found[t] = f'{user} (Wikimedia Commons)'
    time.sleep(1)

filled, still = 0, []
for name, t in need:
    who = found.get(t)
    if who:
        man[name]['artist'] = who
        filled += 1
        print(f'  {name:<24} {who}')
    else:
        still.append((name, t, txt(man[name], 'licence')))

io.open(MAN, 'w', encoding='utf-8').write(
    json.dumps(man, ensure_ascii=False, separators=(',', ':')))

# Anything still uncredited under an attribution licence cannot be shown.
# Dropping a picture costs a picture; shipping it costs the project's claim
# to be built honestly on other people's work.
if still:
    print(f'\n{len(still)} cannot be credited and will be dropped:')
    for n, t, lic in still:
        print(f'   {n}  {lic}  ({t})')
    json.dump([n for n, _, _ in still],
              io.open(r'C:\Android\work\uncredited.json', 'w'))
else:
    json.dump([], io.open(r'C:\Android\work\uncredited.json', 'w'))

# Report, in a form the console cannot mangle.
bad = [n for n, o in man.items()
       if not txt(o, 'artist')
       and 'publicdomain' not in (txt(o, 'licence') + txt(o, 'licurl')).lower()
       and 'public domain' not in txt(o, 'licence').lower()]
print(f'\nfilled {filled}; {len(bad)} photographs remain uncredited '
      f'under an attribution licence')
io.open(r'C:\Android\work\credit_report.json', 'w', encoding='utf-8').write(
    json.dumps({'uncredited': bad,
                'artists': {n: txt(o, 'artist') for n, o in man.items()}},
               ensure_ascii=False, indent=1))
print('wrote credit_report.json')
