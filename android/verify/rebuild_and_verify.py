# -*- coding: utf-8 -*-
"""Pull, copy into the build tree, build, and run every verifier.

Written as a script rather than typed at the prompt because PowerShell has
no heredoc and every attempt to pass Python through it has cost more than
the work it was wrapping.
"""
import os, shutil, subprocess, sys

REPO = r'C:\Android\work\repo'
TREE = r'C:\Android\work\android'
WORK = r'C:\Android\work'

def run(cmd, cwd=None, shell=False):
    print('>', cmd if isinstance(cmd, str) else ' '.join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=cwd, shell=shell)
    return r.returncode

print('=== pull ===', flush=True)
run(['git', 'pull', '--quiet', 'origin', 'main'], cwd=REPO)
run(['git', 'log', '--oneline', '-1'], cwd=REPO)

print('\n=== copy into the build tree ===', flush=True)
src = os.path.join(REPO, r'android\app\src\main')
dst = os.path.join(TREE, r'app\src\main')
shutil.rmtree(os.path.join(dst, r'java\org'), ignore_errors=True)
shutil.copytree(os.path.join(src, r'java\org'), os.path.join(dst, r'java\org'))
os.makedirs(os.path.join(dst, 'assets'), exist_ok=True)
shutil.copy2(os.path.join(src, r'assets\audio.json'),
             os.path.join(dst, r'assets\audio.json'))
shutil.copy2(os.path.join(src, 'AndroidManifest.xml'),
             os.path.join(dst, 'AndroidManifest.xml'))
shutil.copy2(os.path.join(REPO, r'android\app\build.gradle.kts'),
             os.path.join(TREE, r'app\build.gradle.kts'))
print('copied', flush=True)

print('\n=== stage the pictures ===', flush=True)
# 58 MB of WebP, not kept in the source branch. See stage_pictures.py.
if run([sys.executable, '-u', 'stage_pictures.py'], cwd=WORK) != 0:
    print('could not stage the pictures')
    sys.exit(1)

print('\n=== build ===', flush=True)
rc = run([os.path.join(TREE, 'build-debug.bat'), 'assembleDebug'], shell=False)
log = open(os.path.join(TREE, 'build.log'), encoding='utf-8', errors='replace').read()
for line in log.splitlines():
    if (line.startswith('e:') or line.startswith('w:')
            or 'error:' in line or line.startswith('BUILD')
            or line.startswith('EXITCODE')
            or 'FAILED' in line):
        print('  ' + line.strip(), flush=True)
if 'BUILD SUCCESSFUL' not in log:
    print('\nTHE BUILD FAILED', flush=True)
    print(log[-4000:])
    sys.exit(1)

print('\n=== verifiers ===', flush=True)
bad = []
for s in ('verify_apk.py', 'verify_books.py', 'verify_context.py',
          'verify_search.py', 'verify_audio_android.py',
          'verify_pictures_android.py'):
    print(f'\n--- {s}', flush=True)
    rc = run([sys.executable, '-u', s], cwd=WORK)
    if rc != 0:
        bad.append(s)

print('\n' + ('FAILED: ' + ', '.join(bad) if bad
              else 'EVERY ANDROID CHECK PASSED'), flush=True)
sys.exit(1 if bad else 0)
