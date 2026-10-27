# Verifying the APK without a device

There is no emulator on the build machine, so these do what the app does,
in the same order, with the same bytes and the same SQL:

```
AssetManager.open(ASSET)   ->  read the zip entry out of the built APK
GZIPInputStream(...)       ->  gunzip it
SQLiteDatabase.open...     ->  open it read-only
CodexDao / CommentaryDao   ->  run their queries verbatim
```

The Kotlin compiles; the SQL and the packaging are where the bugs are.

| script | what it checks |
|---|---|
| `verify_apk.py` | the assets are present under the names the app opens, stored uncompressed, gunzip to valid databases; then the core and commentary queries |
| `verify_books.py` | the navigation query: 66 books, 1,189 chapters, display names, and that stepping forward from Genesis 1 reaches the last chapter of Revelation |
| `verify_context.py` | notes, cross-references, and everything the About screen must show |
| `verify_search.py` | the three search modes, awkward input, canonical ordering, and the lexicon ranking |

Run `verify_apk.py` first — it unpacks the databases the others read.

```sh
python verify_apk.py && python verify_books.py && python verify_context.py && python verify_search.py
```

Paths at the top of each script point at the Windows build tree; change
them to wherever the APK and the unpacked databases are.

81 checks in all. They found two things a successful build did not:

**The APK packaged the wrong asset.** AAPT special-cases any asset ending
`.gz` — it strips the extension and re-packs the contents, so `codex.db.gz`
arrived as `assets/codex.db` holding the decompressed 456 MB database. The
app opened `codex.db.gz`, which no longer existed. It would have crashed on
first launch, and the build said BUILD SUCCESSFUL.

**The lexicon search was answering the wrong question.** FTS4 matches any
column and has no relevance ranking, so "shepherd" returned the Hebrew for
"idol" first — the word appears somewhere in its definition.
