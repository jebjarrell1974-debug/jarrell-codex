#!/bin/bash
# Full rebuild from pinned sources. Each step is independent and rerunnable.
set -e
cd "$(dirname "$0")/.."
echo "=== run one: the data spine"
for s in 01_manifest 02_tokens 03_morphology 04_lexicon 05_translations 06_versification 07_align_index; do
  echo ">>> $s"; python3 -I "scripts/$s.py" >/dev/null
done
echo "=== run two: places, people, events, dictionary"
for s in 10_geography 11_theographic 13_chronology 17_notes; do
  echo ">>> $s"; python3 -I "scripts/$s.py" >/dev/null
done
echo "=== acceptance"
python3 -I scripts/09_acceptance.py       | tail -3
python3 -I scripts/12_acceptance_run2.py  | tail -3
python3 -I scripts/14_acceptance_chronology.py | tail -3
python3 -I scripts/18_acceptance_notes.py | tail -3
