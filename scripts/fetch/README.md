# Fetchers

These ran once each, from a machine with open internet, and their output was
published to the gh-pages branch. They are here so the work is repeatable,
not because the build runs them.

- `fetch_place_photos.py` / `shrink_photos.py` - Wikidata P18 to Wikimedia
  Commons, then down to WebP under 300 KB.
- `fetch_dore.py` / `shrink_dore.py` - the Commons category "Dore's English
  Bible". The verse reference lives in each file's description, not its title.
- `build_audio.py` - the LibriVox items on archive.org, matched to chapters.
  Reshaped afterwards by `scripts/37_audio_index.py`.
- `fix_credits.py` / `fix_credits2.py` - the attribution repair. Fourteen
  photographs were published under CC BY, CC BY-SA or GPL with no author
  named. The first pass asks Commons for the Artist field; the second falls
  back to the uploading account, which is what Commons' own attribution
  generator does for an own-work file.
