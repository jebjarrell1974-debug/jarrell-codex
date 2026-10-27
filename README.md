# The Jarrell Codex

> *Thy word is a lamp unto my feet, and a light unto my path.*
> — Psalm 119:105

A free, offline Bible for people who want to see what the text actually says.

Every Hebrew, Aramaic and Greek word in scripture is addressable. Tap one and
you get its parsing, its dictionary entry, and every other place that word
appears — on a phone, with no signal, no account, and no price.

**Free forever, in both senses.** No cost, and open source. Nobody should have
to pay to read the Bible in its own language.

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
| **Dictionary** | Easton's 1897, 6,519 senses across 3,964 headwords, 2,818 tied to a named person |
| **Chronology** | Six dated schemes you choose between, never one silently assumed |
| **Context** | 108,925 historical, cultural and linguistic notes across 93% of verses |

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

About four minutes. Needs `python3` and `git`, nothing else — no frameworks,
no package installs. Sources are cloned fresh and pinned by commit hash and
SHA-256 in `build/manifest.json`, so a rebuild is reproducible down to the byte.

The database is a build artifact and is not committed. 287 MB on disk,
about 75 MB compressed — an ordinary app download, which is why the whole
thing ships inside the app instead of needing a server.

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

`android/` holds a Kotlin + Compose client that reads the prebuilt database
straight out of the APK. The database travels gzipped at 61 MB and expands to
about 226 MB on first launch — comfortably inside Google Play's 500 MB base
module limit, so there is no asset pack and no first-run download. Install it
and it works: on a plane, in a basement, on a handed-over phone with no SIM.

**That project has never been compiled.** It was written without an Android
SDK, so the Kotlin and Gradle config are unverified and the first build will
need fixing. The SQL inside it is not a guess — every query was benchmarked
against the real database first (`scripts/15_queries.py`; a chapter opens in
under 2 ms, the worst case is 24.8 ms across all 682,818 morphemes).

`reader/` is a working reference reader over a real slice of the data, built
and tested first so the Compose UI is a port of something known-good.

## Licence

Code is **MPL-2.0**. The data carries its own licences and its own obligations —
see **[ATTRIBUTION.md](ATTRIBUTION.md)**, which must travel with any copy.

Built on the generosity of scholars who gave their work away: Tyndale House
Cambridge, Clear Bible, OpenBible.info, Theographic, and the Westminster
Leningrad Codex through OpenScriptures.
