# -*- coding: utf-8 -*-
"""Fourteen photographs are under licences that require attribution and
carry no photographer.

CC BY, CC BY-SA and GPL all require crediting the author. The fetch took
the file from Wikidata's P18 and the licence from Commons, but for these
fourteen it did not come back with an Artist, so the manifest says null and
both the website and the app show the licence with nobody to credit. That
is the one thing a project built on other people's freely given work must
not do.

The author is in the Commons file page's extmetadata. This asks for it, by
the file title taken from the page URL already in the manifest, and writes
what comes back into pix_manifest.json. Anything still without an author
after this is reported rather than quietly shipped.
"""
import io, json, os, re, sys, time, urllib.parse, urllib.request

GHP = r'C:\Android\work\ghp3'
MAN = os.path.join(GHP, 'data', 'pix_manifest.json')
API = 'https://commons.wikimedia.org/w/api.php'
UA = 'jarrell-codex/1.0 (attribution fixup; https://github.com/jebjarrell1974-debug/jarrell-codex)'

TAGS = re.compile(r'<[^>]+>')


def txt(o, k):
    v = o.get(k)
    return v if isinstance(v, str) else ''


def title_of(page):
    """"File:Foo.jpg" out of a commons.wikimedia.org/wiki/File:Foo.jpg URL."""
    if not page:
        return None
    m = re.search(r'/wiki/(.+)$', page)
    if not m:
        return None
    return urllib.parse.unquote(m.group(1)).replace('_', ' ')


def clean(html):
    """The Artist field is wiki HTML: a link, sometimes a whole template."""
    s = TAGS.sub(' ', html or '')
    s = (s.replace('&amp;', '&').replace('&nbsp;', ' ')
          .replace('&quot;', '"').replace('&#039;', "'"))
    s = re.sub(r'\s+', ' ', s).strip(' ,;|')
    return s[:120]


def ask(titles):
    q = urllib.parse.urlencode({
        'action': 'query', 'format': 'json', 'prop': 'imageinfo',
        'iiprop': 'extmetadata', 'titles': '|'.join(titles),
        'iiextmetadatafilter': 'Artist|Attribution|Credit|LicenseShortName',
    })
    r = urllib.request.Request(API + '?' + q, headers={'User-Agent': UA})
    with urllib.request.urlopen(r, timeout=60) as h:
        return json.load(h)


man = json.load(io.open(MAN, encoding='utf-8'))
need = []
for name, o in man.items():
    if txt(o, 'artist'):
        continue
    lic = (txt(o, 'licence') + ' ' + txt(o, 'licurl')).lower()
    if 'publicdomain' in lic or 'public domain' in lic or 'cc0' in lic:
        continue          # nothing to attribute
    t = title_of(txt(o, 'page'))
    if t:
        need.append((name, t))
    else:
        print(f'  no commons page for {name}')

print(f'{len(need)} photographs need an author')
by_title = {}
for i in range(0, len(need), 20):
    chunk = need[i:i + 20]
    data = ask([t for _, t in chunk])
    for pg in (data.get('query', {}).get('pages', {}) or {}).values():
        t = pg.get('title', '')
        ii = (pg.get('imageinfo') or [{}])[0]
        em = ii.get('extmetadata') or {}
        for field in ('Artist', 'Attribution', 'Credit'):
            v = clean((em.get(field) or {}).get('value', ''))
            if v and v.lower() not in ('unknown', 'anonymous', 'see below'):
                by_title[t] = v
                break
    time.sleep(1)

filled, still = 0, []
for name, t in need:
    who = by_title.get(t)
    if who:
        man[name]['artist'] = who
        filled += 1
        print(f'  {name:<24} {who}')
    else:
        still.append((name, t))

io.open(MAN, 'w', encoding='utf-8').write(
    json.dumps(man, ensure_ascii=False, separators=(',', ':')))
print(f'\nfilled {filled} of {len(need)}')
if still:
    print(f'{len(still)} still have no author Commons will give:')
    for name, t in still:
        print(f'   {name}  ({t})')
    json.dump([n for n, _ in still],
              io.open(r'C:\Android\work\uncredited.json', 'w'))
print('\nwrote ' + MAN)
