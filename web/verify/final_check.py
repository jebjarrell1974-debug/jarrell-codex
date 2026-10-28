# -*- coding: utf-8 -*-
"""Everything that can only be checked against the published site."""
import subprocess, sys

checks = ['verify_live2.py', 'verify_live_audio.py', 'verify_live_credits.py',
          'verify_live_welcome.py', 'verify_live_pano.py']
bad = []
for s in checks:
    print(f'\n{"=" * 62}\n{s}\n{"=" * 62}', flush=True)
    if subprocess.run([sys.executable, '-u', s],
                      cwd=r'C:\Android\work').returncode != 0:
        bad.append(s)
print('\n' + ('FAILED: ' + ', '.join(bad) if bad
              else 'THE LIVE SITE IS GOOD, ALL FIVE CHECKS'))
sys.exit(1 if bad else 0)
