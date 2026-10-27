#!/bin/bash
# Full rebuild from pinned sources. Each step is independent and rerunnable.
set -e
cd "$(dirname "$0")/.."
for s in 01_manifest 02_tokens 03_morphology 04_lexicon 05_translations 06_versification 07_align_index; do
  echo ">>> $s"; python3 -I "scripts/$s.py" >/dev/null
done
echo ">>> acceptance"; python3 -I scripts/09_acceptance.py | tail -3
