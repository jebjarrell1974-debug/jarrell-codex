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

- `verify_live_welcome.py` - the first screen: that a first visit lands on
  it, that the Start button is wired to the click handler, and that it is
  shown once and can be asked for again.
- `verify_live_pano.py` - the photospheres: that every one names an author,
  a licence and a source page, that every image is really 2048x1024 and
  under 360 KB, that the page loads no third-party script, and that no test
  fixture ended up in the offline tier.
- `final_check.py` - runs all five in order.

Two checks in here used to assert a tier count by hand. "six download
tiers" was true until the photospheres made it seven, and then it was a
failing test about nothing. Both now assert what actually matters - that
every tier the manifest declares has files, a size and words saying what it
is - which keeps being true the next time one is added.
