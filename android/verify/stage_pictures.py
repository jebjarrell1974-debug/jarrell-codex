# -*- coding: utf-8 -*-
"""Put the photographs and engravings into the Android build tree.

They are not committed to main. The pictures were fetched on this machine
and published to gh-pages, which is where the website serves them from, and
duplicating 60 MB of WebP into the source branch would buy nothing. The
databases work the same way, so this follows the precedent rather than
inventing one.
"""
import os, shutil, subprocess, sys

GHP = r'C:\Android\work\ghp3'
ASSETS = r'C:\Android\work\android\app\src\main\assets'

print('refreshing the gh-pages clone', flush=True)
subprocess.run(['git', 'pull', '--quiet', 'origin', 'gh-pages'], cwd=GHP)
print(' ', subprocess.run(['git', 'log', '--oneline', '-1'], cwd=GHP,
                          capture_output=True, text=True).stdout.strip(), flush=True)

os.makedirs(ASSETS, exist_ok=True)
total = 0
for name in ('pix', 'dore'):
    src = os.path.join(GHP, 'data', name)
    dst = os.path.join(ASSETS, name)
    if not os.path.isdir(src):
        print(f'MISSING: {src}')
        sys.exit(1)
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst)
    n = len(os.listdir(dst))
    b = sum(os.path.getsize(os.path.join(dst, f)) for f in os.listdir(dst))
    total += b
    print(f'  {name:<5} {n:>4} files  {b / 1048576:6.1f} MB', flush=True)

for name in ('pix_manifest.json', 'dore.json', 'audio.json'):
    src = os.path.join(GHP, 'data', name)
    if not os.path.isfile(src):
        print(f'MISSING: {src}')
        sys.exit(1)
    shutil.copy2(src, os.path.join(ASSETS, name))
    b = os.path.getsize(src)
    total += b
    print(f'  {name:<18} {b / 1024:7.0f} KB', flush=True)

print(f'\nstaged {total / 1048576:.1f} MB of pictures and manifests into assets')
