# -*- coding: utf-8 -*-
"""One URL, six tries, long waits. Is Romans 1 gone, or was archive.org
simply tired of us by the 375th request?"""
import sys, time, urllib.request

U = 'https://archive.org/download/romans_kjv_1408_librivox/romans_01_kjv_64kb.mp3'
META = 'https://archive.org/metadata/romans_kjv_1408_librivox'
UA = {'User-Agent': 'jarrell-codex-verify'}

print('the item still exists?')
try:
    r = urllib.request.Request(META, headers=UA)
    with urllib.request.urlopen(r, timeout=60) as h:
        import json
        m = json.load(h)
    files = [f['name'] for f in m.get('files', [])
             if f['name'].endswith('_64kb.mp3')]
    print(f'  item has {len(files)} 64kb files')
    print('  romans_01_kjv_64kb.mp3 listed:',
          'romans_01_kjv_64kb.mp3' in files)
    print('  first few:', files[:4])
except Exception as e:
    print('  metadata failed:', repr(e)[:90])

print('\nthe file itself')
for k in range(6):
    try:
        r = urllib.request.Request(U, method='HEAD', headers=UA)
        with urllib.request.urlopen(r, timeout=90) as h:
            print(f'  try {k + 1}: {h.status} {h.headers.get("content-type")} '
                  f'{int(h.headers.get("content-length") or 0)} bytes')
            sys.exit(0)
    except Exception as e:
        print(f'  try {k + 1}: {repr(e)[:80]}')
        time.sleep(10 + 15 * k)
print('\nstill failing after six tries over two minutes')
sys.exit(1)
