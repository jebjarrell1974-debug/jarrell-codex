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

The database is a build artifact and is not committed. 226 MB on disk,
about 60 MB compressed — an ordinary app download, which is why the whole
thing ships inside the app instead of needing a server.

## Is it right?

`scripts/09_acceptance.py` and `scripts/12_acceptance_run2.py` prove the thing
works before anything is built on it: 35 checks, 0 failures. It walks the first word of Genesis 1:1 and of
John 1:1 through all five layers, confirms the versification actually
reconciles (KJV 2 Corinthians 13:14 resolves to the Greek 13:13), and refuses
to pass on orphan rows or unresolved morphology.

Counts were cross-checked against two independent projects. The Greek agrees
with MACULA's Nestle 1904 to within 0.57%, and the only books that differ by
more than a handful of words are Mark, John and Luke — the longer ending of
Mark, the woman taken in adultery, and the agony in the garden. Those are real
differences between critical editions, not mistakes, and the database keeps
every variant rather than quietly picking a side.

## Honesty about places

A place the data can locate gets coordinates. A place scholars argue about is
marked **disputed**. A place genuinely lost — the land of Nod, east of Eden —
comes back **unknown**, with no coordinates at all rather than a pin someone
invented. Regions like Egypt are marked as regions, not as mysteries.

## Licence

Code is **MPL-2.0**. The data carries its own licences and its own obligations —
see **[ATTRIBUTION.md](ATTRIBUTION.md)**, which must travel with any copy.

Built on the generosity of scholars who gave their work away: Tyndale House
Cambridge, Clear Bible, OpenBible.info, Theographic, and the Westminster
Leningrad Codex through OpenScriptures.
