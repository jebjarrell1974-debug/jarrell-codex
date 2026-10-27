# -*- coding: utf-8 -*-
"""Everything that can only be checked against the published site."""
import subprocess, sys

bad = []
for s in ('verify_live2.py', 'verify_live_audio.py', 'verify_live_credits.py'):
    print(f'\n{"=" * 60}\n{s}\n{"=" * 60}', flush=True)
    r = subprocess.run([sys.executable, '-u', s], cwd=r'C:\Android\work')
    if r.returncode != 0:
        bad.append(s)
print('\n' + ('FAILED: ' + ', '.join(bad) if bad else 'THE LIVE SITE IS GOOD'))
sys.exit(1 if bad else 0)
