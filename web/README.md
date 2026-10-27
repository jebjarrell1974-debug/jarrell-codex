# The mobile reader

The whole study apparatus in a phone browser: no install, no account,
no server. Works in Safari on an iPhone and Chrome on Android.

## What is here

| file | what it is |
|---|---|
| `index.html` | the shell |
| `app.js` | the entire reader — routing, rendering, word study, search |
| `app.css` | styling, light and dark, phone-first |
| `sw.js` | service worker: precaches the shell and fonts, then keeps every chapter you open |
| `font/` | the three typefaces, served from here rather than a CDN |
| `manifest.webmanifest` | lets it be added to a home screen and run full-screen |

No framework, no build step, no bundler. Open `index.html` over any static
server and it runs.

## The data it reads

`app.js` fetches from `data/`, which is **not** in this branch — it is
generated. Build it with:

```
python3 scripts/26_site_data.py     # per-chapter JSON, 1,189 files
python3 scripts/27_site_study.py    # concordance, places, people, events, dictionary
python3 scripts/28_site_search.py   # sharded inverted indexes
python3 scripts/29_shard_lexicon.py # split the lexicon so a word tap costs ~30 KB
```

Everything is sharded so that one tap or one search word fetches one small
file. Nothing loads the whole Bible into memory. Startup is 369 KB.

The built site, data and all, lives on the `gh-pages` branch.
