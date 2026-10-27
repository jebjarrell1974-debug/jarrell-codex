#!/bin/bash
# Full rebuild from pinned sources. Each step is independent and rerunnable.
set -e
cd "$(dirname "$0")/.."

echo "=== the data spine"
for s in 01_manifest 02_tokens 03_morphology 04_lexicon 05_translations \
         06_versification 07_align_index; do
  echo ">>> $s"; python3 -I "scripts/$s.py" >/dev/null
done

echo "=== context: places, people, events, dictionary, chronology, notes"
for s in 10_geography 11_theographic 13_chronology 17_notes; do
  echo ">>> $s"; python3 -I "scripts/$s.py" >/dev/null
done

echo "=== study tools: search, cross-references, full lexicon, names, semantics"
for s in 19_search 21_xrefs 22_lsj_names 24_semantics; do
  echo ">>> $s"; python3 -I "scripts/$s.py" >/dev/null
done

echo "=== acceptance"
for s in 09_acceptance 12_acceptance_run2 14_acceptance_chronology \
         18_acceptance_notes 23_acceptance_search 25_acceptance_semantics; do
  python3 -I "scripts/$s.py" | tail -2
done
echo ">>> reference parsing"; python3 -I scripts/20_reference.py | tail -1
