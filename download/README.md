The whole Bible in the original languages, parsed word by word, with the
lexicons, the concordance, the places, the people, the dates, the
translators' notes and six commentaries — assembled from ten open sources
into one database that works with no connection at all.

## Read it right now, on any phone

**https://jebjarrell1974-debug.github.io/jarrell-codex/**

Nothing to install. Works in Safari on an iPhone and Chrome on Android.
Add it to the home screen and it runs full-screen like an app. After the
first visit, every chapter you open keeps working with no signal.

## What is in the database

| | |
|---|---|
| verses | 31,219 |
| words of Hebrew, Aramaic and Greek | 447,744 |
| morphemes, each with its own Strong's number and parsing | 682,818 |
| lexicon entries | 21,232 brief, 9,549 full |
| English translations | 4, public domain, 124,408 verses |
| places | 1,342, each marked identified, disputed, region or not located |
| people | 3,067 |
| events | 450, dated under 6 chronologies |
| dictionary entries | 6,519 |
| translation notes | 108,925 |
| cross-references | 432,949, weighted |
| commentary units | 91,008 across 6 commentators |

## The files

**`bible.db.gz.part00` + `bible.db.gz.part01`** — 132 MB compressed in two
pieces, 456 MB unpacked. GitHub will not host a single file over 100 MB, so
take both parts and join them:

```sh
# Mac or Linux
cat bible.db.gz.part* > bible.db.gz
gunzip bible.db.gz
```
```bat
rem Windows
copy /b bible.db.gz.part00 + bible.db.gz.part01 bible.db.gz
```

The joined file's SHA-256 is in `SHA256SUMS.txt`; check it before you trust it.
It holds The text, the
parsing, the lexicons, the translations, the places, the people, the
events, the chronologies, the dictionary, the notes, the cross-references
and the search indexes.

**`commentary.db.gz`** — 48 MB compressed, 148 MB unpacked. Matthew Henry,
the 1599 Geneva notes, Calvin, Poole, Trapp and Spurgeon, keyed to the
verse. Kept separate so a phone that is short of room can skip it:

```sql
ATTACH 'commentary.db' AS cm;
SELECT m.author, c.body
  FROM cm.commentary_verse v
  JOIN cm.commentary c   ON c.unit_id   = v.unit_id
  JOIN cm.commentator m  ON m.source_id = c.source_id
 WHERE v.verse_key = 'Jhn.3.16'
 ORDER BY m.sort;
```

Verify what you downloaded against `SHA256SUMS.txt`.

## What is not here yet

**Audio.** It needs a licence from the people who recorded it, and that
request is still outstanding. Everything else works without it.

## Licence

Code is MPL-2.0. The assembled data is CC BY-SA 4.0, because
unfoldingWord's translation notes are share-alike and that carries.

Take it, copy it, put it on a memory stick, hand it out. That is what it
is for. Nothing in here is licensed in a way that would stop you — two
larger commentary collections were deliberately left out for exactly that
reason, and `ATTRIBUTION.md` says which and why.
