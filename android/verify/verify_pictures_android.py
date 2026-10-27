# -*- coding: utf-8 -*-
"""Replay Pictures.kt's data path against the built APK.

No emulator here, so the check is: pull the manifests out of the APK the
way the app pulls them, resolve every plate and photograph the way
Pictures.kt resolves them, and confirm the file each one names is actually
in the APK and is actually an image. A build that succeeds proves the code
compiles; this proves the pictures it will ask for are there.
"""
import glob, json, os, sys, zipfile

fails = []

def chk(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name +
          (('  ' + str(detail)[:170]) if detail and not cond else ''))
    if not cond:
        fails.append(name)

apk = sorted(glob.glob(r'C:\Android\work\android\app\build\outputs\apk\debug\*.apk'))[0]
z = zipfile.ZipFile(apk)
names = set(z.namelist())
print(f'{os.path.basename(apk)}  {os.path.getsize(apk) / 1048576:.1f} MB')

print('\nthe manifests')
for n in ('assets/pix_manifest.json', 'assets/dore.json'):
    chk(f'{n} is in the apk', n in names)
if fails:
    print('\nFAILED: the manifests are not in the apk')
    sys.exit(1)
pix = json.loads(z.read('assets/pix_manifest.json').decode('utf-8'))
dore = json.loads(z.read('assets/dore.json').decode('utf-8'))
chk('307 photographs', len(pix) == 307, len(pix))
chk('150 plates', len(dore['plates']) == 150, len(dore['plates']))
chk('the plates are keyed to verses', len(dore['at']) > 100, len(dore['at']))

print('\nevery picture the app will ask for')
# Pictures.kt builds "pix/<file>" and "dore/<file>"; the asset path in the
# apk is "assets/" plus that, so the check is the app's own arithmetic.
missing, tiny, notimg = [], [], []
WEBP = b'RIFF'
for name, o in pix.items():
    a = 'assets/pix/' + o['file']
    if a not in names:
        missing.append(a); continue
    info = z.getinfo(a)
    if info.file_size < 2000:
        tiny.append((a, info.file_size))
    if z.read(a)[:4] != WEBP:
        notimg.append(a)
chk('every photograph named by the manifest is in the apk', not missing, missing[:5])
chk('none is a stub', not tiny, tiny[:4])
chk('every one is a real WebP', not notimg, notimg[:4])

missing, notimg, stored = [], [], 0
for pid, o in dore['plates'].items():
    a = 'assets/dore/' + o['file']
    if a not in names:
        missing.append(a); continue
    if z.read(a)[:4] != WEBP:
        notimg.append(a)
    if z.getinfo(a).compress_type == 0:
        stored += 1
chk('every engraving named by the manifest is in the apk', not missing, missing[:5])
chk('every one is a real WebP', not notimg, notimg[:4])
chk('they are stored, not deflated again (noCompress covers webp)',
    stored == len(dore['plates']), f'{stored}/{len(dore["plates"])}')

print('\nresolution, as Pictures.platesAt() does it')
bad = [k for k, ids in dore['at'].items()
       if any(i not in dore['plates'] for i in ids)]
chk('every verse points at plates that exist', not bad, bad[:5])
bad = [k for k in dore['at'] if len(k.split('.')) != 3]
chk('every key is a verse, not a chapter', not bad, bad[:5])
placed = sum(len(v) for v in dore['at'].values())
print(f'       {placed} of {len(dore["plates"])} plates are placed at a verse')
chk('most of the plates are placed', placed >= 120, placed)

print('\nthe decode sizes Pictures.bitmap() will work with')
def sample(w, target=1000):
    s = 1
    while w // (s * 2) >= target:
        s *= 2
    return s
worst = 0
for o in list(pix.values()) + list(dore['plates'].values()):
    w, h = o.get('w', 0), o.get('h', 0)
    if w <= 0 or h <= 0:
        continue
    s = sample(w)
    worst = max(worst, (w // s) * (h // s) * 4)
chk(f'the largest decode is {worst / 1048576:.1f} MB', worst < 6 * 1048576,
    f'{worst / 1048576:.1f} MB')

print('\nattribution, which the licences require')
# An explicit null is not a missing key, and both appear here.
def txt(o, k):
    v = o.get(k)
    return v if isinstance(v, str) else ''

pd = lambda o: ('publicdomain' in txt(o, 'licurl').lower()
                or 'public domain' in txt(o, 'licence').lower())
no_art = [n for n, o in pix.items() if not txt(o, 'artist') and not pd(o)]
chk('every photograph names a photographer or is public domain',
    not no_art, no_art[:5])
no_lic = [n for n, o in pix.items() if not txt(o, 'licence')]
chk('every photograph names a licence', not no_lic, no_lic[:5])
no_page = [n for n, o in pix.items() if not txt(o, 'page')]
chk('every photograph links where it came from', not no_page, no_page[:5])
no_page = [k for k, o in dore['plates'].items() if not txt(o, 'page')]
chk('every engraving links where it came from', not no_page, no_page[:5])

# The nulls themselves, stated rather than smoothed over: whatever reads
# this manifest has to turn each of them into nothing, not into "null".
nulls = {}
for o in list(pix.values()) + list(dore['plates'].values()):
    for k, v in o.items():
        if v is None:
            nulls[k] = nulls.get(k, 0) + 1
print('       explicit nulls in the manifests: '
      + (', '.join(f'{k}={v}' for k, v in sorted(nulls.items())) or 'none'))
dk_pre = open(os.path.join(
    r'C:\Android\work\repo\android\app\src\main\java\org\jarrellcodex',
    'data', 'Pictures.kt'), encoding='utf-8').read()
chk('the parser asks isNull rather than trusting optString',
    'isNull(key)' in dk_pre and 'o.text(' in dk_pre)
chk('and no picture field still goes through optString for text',
    'optString("licurl"' not in dk_pre and 'optString("artist"' not in dk_pre
    and 'optString("ref"' not in dk_pre)

src = r'C:\Android\work\repo\android\app\src\main\java\org\jarrellcodex'
ui = open(os.path.join(src, r'ui\Pictures.kt'), encoding='utf-8').read()
print('\nthe code that draws them')
chk('the engraving credits Dore and the year', 'Gustave Dor' in ui and '1866' in ui)
chk('and says it is public domain', 'Public domain' in ui)
chk('the photograph credits the photographer', 'photo.artist' in ui)
chk('and links both the source page and the licence',
    'photo.page' in ui and 'photo.licenceUrl' in ui)
chk('space is reserved before the bitmap arrives', 'aspectRatio' in ui)
dk = open(os.path.join(src, r'data\Pictures.kt'), encoding='utf-8').read()
chk('decoding is downsampled to the drawn width', 'inSampleSize' in dk)
chk('the cache is measured in kilobytes, not entries',
    'byteCount / 1024' in dk)
chk('a missing manifest yields null, not a crash', 'getOrNull()' in dk)

print('\n' + ('FAILED: ' + ', '.join(fails) if fails else 'ALL CHECKS PASSED'))
sys.exit(1 if fails else 0)
