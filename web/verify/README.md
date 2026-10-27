# Verifying the published site

These run from a machine with an ordinary internet connection, because the
container that builds the site cannot reach archive.org or Wikimedia and so
cannot check that the things the site points at are actually there.

    python verify_live_all.py

- `verify_live2.py` - the shell, the code, the data files, the pictures, the
  service worker's content stamp, the offline tiers.
- `verify_live_audio.py` - the published audio index, and a HEAD against all
  375 readings. Serially, with retries: twelve concurrent requests made
  archive.org return twenty 500s, none of which were missing files. A 404 is
  reported as gone; a 5xx is set aside, rested for a minute and asked again,
  because by the 375th request the server starts declining to answer and a
  verifier that cries wolf gets ignored.
- `verify_live_credits.py` - that every photograph under an attribution
  licence names its author, in the manifest the site actually serves. Fourteen
  once did not.
