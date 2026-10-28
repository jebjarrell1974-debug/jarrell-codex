# The Jarrell Codex

> *Thy word is a lamp unto my feet, and a light unto my path.*
> — Psalm 119:105

A free, offline Bible for people who want to see what the text actually says.

Every Hebrew, Aramaic and Greek word in scripture is addressable. Tap one and
you get its parsing, its dictionary entry, and every other place that word
appears — on a phone, with no signal, no account, and no price.

**Free forever, in both senses.** No cost, and open source. Nobody should have
to pay to read the Bible in its own language.

## Open it now

**https://jebjarrell1974-debug.github.io/jarrell-codex/**

Nothing to install, nothing to sign up for. Works in Safari on an iPhone and
Chrome on Android. Add it to the home screen and it runs full-screen like an
app. After the first visit, every chapter you have opened keeps working with
no signal.

Or take the whole database and carry it off: **[downloads](https://jebjarrell1974-debug.github.io/jarrell-codex/download/)**.

---

## What it does

| Layer | What you get |
|---|---|
| **Original text** | 447,744 Hebrew, Aramaic and Greek words from the Leningrad Codex and the amalgamated Greek New Testament |
| **Morphology** | Full parsing on every one — person, gender, number, tense, voice, mood, stem, state |
| **Lexicon** | 21,232 entries (abridged BDB for Hebrew, Abbott-Smith for Greek), keyed to extended Strong's |
| **Concordance** | Every other occurrence of any word, as a live query rather than a stored list |
| **Translations** | KJV, ASV, Darby and Young's Literal, aligned verse by verse to the original |
| **Geography** | 1,342 places with coordinates, confidence ratings and Wikidata links |
| **Versification** | 20,623 mappings reconciling English, Hebrew, Greek and Latin verse numbering |
| **People** | 3,067 people with dates, linked to 28,240 verses |
| **Events** | A 450-event timeline, linked to 17,570 verses |
| **Dictionary** | Easton's 1897, 6,519 senses under 6,517 headwords, tied to named people where known |
| **Cross-references** | 432,949, weighted by how strongly the two passages have been linked |
| **Commentary** | 91,008 units from six commentators written between 1599 and 1885, covering 99.6% of verses |
| **Search** | Verse text, English gloss to original word, dictionary headwords, and the notes |
| **Chronology** | Six dated schemes you choose between, never one silently assumed |
| **Context** | 108,925 historical, cultural and linguistic notes across 93% of verses |
| **Audio** | All 1,189 chapters read aloud, from public-domain LibriVox recordings streamed from archive.org |

## The idea in one sentence

The atom is the **morpheme**, not the word.

One printed Hebrew word often carries a prefix, a root and a suffix, each with
its own Strong's number and its own grammar. `בְּרֵאשִׁית` is not one word,
it is `H9003` *in* plus `H7225G` *beginning*. Greek crasis works the same way:
`κἀγώ` is `καί` plus `ἐγώ`. Build on the printed word and the concordance
quietly lies to you. Build on the morpheme and every other layer — dictionary,
places, notes, audio — hangs off two stable keys and nothing has to be redone.

## Build it

    ./scripts/build_all.sh

Then, for the website:

    python3 scripts/26_site_data.py        # per-chapter JSON
    python3 scripts/27_site_study.py       # concordance, places, people, events, dictionary
    python3 scripts/28_site_search.py      # sharded inverted indexes
    python3 scripts/29_shard_lexicon.py    # split the lexicon for cheap word taps
    python3 scripts/30_commentary.py       # the six commentators
    python3 scripts/31_commentary_index.py # per-verse counts into the chapter files
    python3 scripts/32_stamp_build.py      # content digest into the service worker
    python3 scripts/33_commentary_db.py    # commentary.db for the clients

About four minutes for the database. Needs `python3` and `git`, nothing else — no frameworks,
no package installs. Sources are cloned fresh and pinned by commit hash and
SHA-256 in `build/manifest.json`, so a rebuild is reproducible down to the byte.

The database is a build artifact and is not committed. 456 MB on disk,
132 MB compressed, with the commentary a further 148 MB / 48 MB in a second
file you can attach or ignore. Both are published as downloads, so nobody has
to rebuild anything to get the whole thing.

## Is it right?

`scripts/09_acceptance.py` and `scripts/12_acceptance_run2.py` prove the thing
works before anything is built on it: 59 checks, 0 failures. It walks the first word of Genesis 1:1 and of
John 1:1 through all five layers, confirms the versification actually
reconciles (KJV 2 Corinthians 13:14 resolves to the Greek 13:13), and refuses
to pass on orphan rows or unresolved morphology.

Counts were cross-checked against two independent projects. The Greek agrees
with MACULA's Nestle 1904 to within 0.57%, and the only books that differ by
more than a handful of words are Mark, John and Luke — the longer ending of
Mark, the woman taken in adultery, and the agony in the garden. Those are real
differences between critical editions, not mistakes, and the database keeps
every variant rather than quietly picking a side.

## Honesty about dates

There is no single biblical chronology, and an app that shows one date without
saying whose it is has quietly made a choice for you.

So dates are per scheme. Ussher puts creation at 4004 BC, Floyd Nolen Jones at
4003. For the division of the kingdom after Solomon, the genealogical schemes
say 974 BC and Thiele says 931 — a 43-year gap in a period both sides consider
well documented. The app shows you whose number you are looking at and lets you
switch.

Where a scheme has no date for an event, it returns nothing and says so. It
never borrows another scheme's year and presents it as that scheme's answer.
A blank is information. Four built-in notes explain why the schemes diverge,
what is actually fixed by external records, and how to choose.

## Honesty about places

A place the data can locate gets coordinates. A place scholars argue about is
marked **disputed**. A place genuinely lost — the land of Nod, east of Eden —
comes back **unknown**, with no coordinates at all rather than a pin someone
invented. Regions like Egypt are marked as regions, not as mysteries.

## The app

`web/` is the one that is finished. Plain HTML, CSS and JavaScript — no
framework, no build step, no bundler — reading sharded JSON so a word tap
costs about 30 KB and startup costs 369 KB. A service worker keeps the shell,
the fonts and every chapter you open, so it works with no signal. Fonts are
vendored rather than loaded from a CDN: offline has to mean offline, and
opening your Bible should not make a request to anybody. Sixty browser checks
run against it at phone viewport, including a first-visit offline test in a
clean profile.

`android/` holds a Kotlin + Compose client that reads the prebuilt database
straight out of the APK. It compiles. The SQL is not a guess — every query was
benchmarked against the real database first (`scripts/15_queries.py`; a chapter
opens in 1.6 ms, the worst case is 24.8 ms across all 682,818 morphemes). It
does not yet show the commentary layer.

`reader/` is a reference reader over a real slice of the data, built and tested
first so the client UI was a port of something known-good.

## Listening

Every chapter has a **Listen** button at the top and the bottom. The readings
are LibriVox recordings, read by volunteers and
released into the public domain, so they need no licence and no permission.
They stream from archive.org rather than being copied here, which means
Listen needs a connection even when the text does not. Most of those files
hold several chapters, so the player starts at an estimated point inside the
file and says that it is an estimate.

## What is missing

**Offline audio.** The readings stream; they are not part of the offline copy.
The text, the study layers and the pictures all work with no signal, but the
spoken word still needs one.

## Licence

Code is **MPL-2.0**. The data carries its own licences and its own obligations —
see **[ATTRIBUTION.md](ATTRIBUTION.md)**, which must travel with any copy.

Two larger commentary collections were available and were deliberately left
out: one carries an explicit fair-use notice over excerpts still under
copyright, the other dates its translations as "19th-century and later". Fair
use is a defence tied to a particular use and does not travel to everyone
downstream. This is meant to be copied by people who will never open a licence
file, so anything whose terms cannot be stood behind is not in it.
ATTRIBUTION.md records which and why.

Built on the generosity of scholars who gave their work away: Tyndale House
Cambridge, Clear Bible, OpenBible.info, Theographic, unfoldingWord, and the
Westminster Leningrad Codex through OpenScriptures. And on six commentators
who have been dead for between a century and four hundred years, and who are
still arguing.
