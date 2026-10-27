# -*- coding: utf-8 -*-
"""Replay AudioIndex's own data path against the built APK.

There is no emulator here, so the check is to read the asset out of the
APK exactly as the app does, resolve chapters the way AudioIndex.kt
resolves them, and work out the starting fraction the way Reading.fraction
works it out. A build that succeeds proves the code compiles; this proves
the data it will read is the data it expects.
"""
import glob, json, os, sys, zipfile

fails = []

def chk(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name +
          (('  ' + str(detail)[:160]) if detail and not cond else ''))
    if not cond:
        fails.append(name)

apk = sorted(glob.glob(r'C:\Android\work\android\app\build\outputs\apk\debug\*.apk'))[0]
z = zipfile.ZipFile(apk)
print(f'{os.path.basename(apk)}  {os.path.getsize(apk) / 1048576:.1f} MB')

print('\nthe asset')
names = z.namelist()
chk('assets/audio.json is in the apk', 'assets/audio.json' in names)
raw = z.read('assets/audio.json').decode('utf-8')
ix = json.loads(raw)
chk('it parses as the app will parse it', isinstance(ix, dict))
for k in ('files', 'chapters', 'sources'):
    chk(f'it has "{k}", which AudioIndex requires', k in ix)

print('\nresolution, as AudioIndex.reading() does it')
files, chapters, sources = ix['files'], ix['chapters'], ix['sources']
chk('1189 chapters', len(chapters) == 1189, len(chapters))
chk('375 files', len(files) == 375, len(files))

def reading(key):
    p = chapters.get(key)
    if p is None:
        return None
    f = files[p[0]]
    return dict(url=f['u'], covers=f['ch'], verses=f['vs'], at=p[1],
                mb=f.get('mb', 0.0), item=f['item'])

bad = []
for key in chapters:
    r = reading(key)
    if r is None or r['covers'][r['at']] != key:
        bad.append(key)
    elif len(r['covers']) != len(r['verses']):
        bad.append(key + ' (verse counts out of step)')
    elif r['item'] not in sources:
        bad.append(key + ' (uncredited source)')
chk('every chapter resolves to its own place in its own file', not bad, bad[:5])

print('\nthe starting fraction, as Reading.fraction does it')
def fraction(r):
    total = sum(r['verses'])
    if total <= 0 or r['at'] <= 0:
        return 0.0
    return sum(r['verses'][:r['at']]) / total

# Every value has to be a usable fraction, and the first chapter of a file
# must be 0 - the app treats a non-zero fraction as "this is an estimate"
# and says so, which would be a lie at the start of the file.
off = [k for k in chapters if not 0.0 <= fraction(reading(k)) < 1.0]
chk('every fraction lies in [0, 1)', not off, off[:5])
firsts = [f['ch'][0] for f in files]
off = [k for k in firsts if fraction(reading(k)) != 0.0]
chk('a file\'s first chapter is never called an estimate', not off, off[:5])
alone = [f['ch'][0] for f in files if len(f['ch']) == 1]
# 284, not 280: Obadiah, 2 John, 3 John and Jude are one-chapter books
# that the complete-Bible set gives a file each, and their source titles
# read as ranges, so the build's own 'exact' flag called them excerpts.
chk(f'{len(alone)} chapters have a file to themselves', len(alone) == 284, len(alone))
chk('the index agrees about which those are',
    sorted(alone) == sorted(f['ch'][0] for f in files if f.get('one')),
    len([f for f in files if f.get('one')]))
off = [k for k in alone if fraction(reading(k)) != 0.0]
chk('none of those gets an estimate', not off, off[:5])
# and the fractions inside one file must rise
worst = None
for f in files:
    if len(f['ch']) < 2:
        continue
    fr = [fraction(reading(k)) for k in f['ch']]
    if any(b <= a for a, b in zip(fr, fr[1:])):
        worst = f['ch'][0]
        break
chk('fractions rise through a file', worst is None, worst)

print('\na few by hand')
for key, want_covers in (('Gen.1', 14), ('Psa.23', 32), ('Jhn.3', 8), ('Jos.6', 1)):
    r = reading(key)
    f = fraction(r)
    print(f'  {key:<8} {len(r["covers"]):>3} chapters in the file, '
          f'starts at {f * 100:5.1f}%  {r["covers"][0]} to {r["covers"][-1]}')
    chk(f'{key} sits in a file of {want_covers}', len(r['covers']) == want_covers,
        len(r['covers']))

print('\nthe code that reads it')
src = r'C:\Android\work\repo\android\app\src\main\java\org\jarrellcodex'
def read(p):
    return open(os.path.join(src, p), encoding='utf-8').read()
ai = read(r'data\AudioIndex.kt')
chk('AudioIndex reads the asset by the name the apk uses',
    '"audio.json"' in ai)
chk('a parse failure yields null, not a crash', 'getOrNull()' in ai)
bar = read(r'ui\AudioBar.kt')
chk('the bar calls the position an estimate', 'an estimate for' in bar)
chk('and says it came from verse counts rather than a timing',
    'verse counts' in bar and 'timing anyone recorded' in bar)
chk('and says the audio is not stored on the phone',
    'not stored on this phone' in bar)
chk('and credits LibriVox and the public domain',
    'LibriVox' in bar and 'Public domain' in bar)
pb = read(r'audio\Playback.kt')
chk('a failed service does not stop the audio',
    'may stop if you leave the app' in pb)
chk('asking for a chapter already playing does not restart the file',
    'cur.reading?.url == r.url' in pb)
man = open(r'C:\Android\work\repo\android\app\src\main\AndroidManifest.xml', encoding='utf-8').read()
chk('INTERNET is declared', 'android.permission.INTERNET' in man)
chk('the media-playback service type is declared',
    'FOREGROUND_SERVICE_MEDIA_PLAYBACK' in man and 'mediaPlayback' in man)
chk('and the manifest says why the network is there at all',
    'archive.org' in man)

print('\n' + ('FAILED: ' + ', '.join(fails) if fails else 'ALL CHECKS PASSED'))
sys.exit(1 if fails else 0)
