#!/usr/bin/env python3
"""Stamp the service worker with a digest of the published data.

Cache-first is right for a Bible that has to work with no signal, but it
means a returning reader keeps whatever they downloaded the first time.
Tying the cache name to the content means a rebuild invalidates it exactly
once, and only when something actually changed.
"""
import hashlib, os, re, sys

SITE = '/home/claude/site'
h = hashlib.sha256()
n = 0
for root, dirs, files in os.walk(f'{SITE}/data'):
    dirs.sort()
    for fn in sorted(files):
        p = os.path.join(root, fn)
        h.update(os.path.relpath(p, SITE).encode())
        h.update(str(os.path.getsize(p)).encode())
        with open(p, 'rb') as f:
            h.update(f.read(4096))          # head of each file is enough
        n += 1
# the client code is part of the build too
for fn in ('app.js', 'app.css', 'index.html'):
    with open(f'{SITE}/{fn}', 'rb') as f:
        h.update(f.read())

build = h.hexdigest()[:12]
sw = open(f'{SITE}/sw.js', encoding='utf-8').read()
new = re.sub(r"const BUILD = '[^']*';", f"const BUILD = '{build}';", sw, count=1)
if new == sw and f"'{build}'" not in sw:
    print("FAILED: no BUILD line to stamp in sw.js", file=sys.stderr); sys.exit(1)
open(f'{SITE}/sw.js', 'w', encoding='utf-8').write(new)
print(f"hashed {n:,} data files")
print(f"build  {build}")
