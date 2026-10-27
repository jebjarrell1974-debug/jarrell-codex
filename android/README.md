# Jarrell Codex — Android client

Kotlin + Jetpack Compose. Reads the prebuilt database from `scripts/build_all.sh`.

## Build

    gradle :app:assembleDebug

Verified on: **Gradle 8.7, JDK 17 (Temurin), SDK platform android-34,
build-tools 34.0.0.** Those versions are pinned in `gradle/libs.versions.toml`
and the project is pinned to match them — AGP 8.5.2 is the newest that Gradle
8.7 accepts, since AGP 8.7 demands Gradle 8.9.

Put the real database in place before a release build:

    gzip -9 -c build/bible.db > android/app/src/main/assets/codex.db.gz

The asset is gitignored. A debug build will compile with any valid gzip there,
but the app will have nothing to read.

## Why there is no Room

The database is prebuilt, read-only, and never migrated. Room verifies every
`@Query` at compile time against a schema assembled from declared `@Entity`
classes, which would mean restating all 19 tables purely to satisfy a check on
a generated file — a second source of truth, free to drift from the real one.
Room's migration machinery is dead weight for an asset that ships fixed.

This was not a guess. The Room version of this project failed to compile with
22 errors, all of the form `no such table: token`, because Room could only see
the single entity that had been declared. Plain `android.database.sqlite` is
less code, has no drift, and drops two dependencies and the whole annotation
processor from the build.

## How the database ships

Gzipped in `app/src/main/assets/codex.db.gz` at 61 MB, expanded to about
226 MB in app storage on first launch. It unpacks to a `.part` file and is
renamed into place, so a kill mid-unpack cannot leave a half-written database
that looks complete on the next run.

Google Play's limit for a base module is 500 MB compressed, so the whole
database fits with no asset pack and no first-run download. That is the point:
the app works the moment it is installed, with no signal and no account.

## Three behaviours that are load-bearing

Ported from a reference reader that was built and tested against the same data
first. Do not "simplify" these away:

1. **Tapping a word shows its morphemes, not just the word.** One printed
   Hebrew word can hold a prefix, root and suffix with separate Strong's
   numbers. `בְּרֵאשִׁית` is `H9003` *in* + `H7225G` *beginning*.
2. **The concordance searches simple Strong's.** A reader with a printed
   concordance types `H3068`, not the disambiguated `H3068G`. Searching the
   extended number alone finds nothing for them — verified: `H3068` returns
   6,528 occurrences, `H3068G` alone would miss two of its three senses.
3. **A chronology scheme with no date says so.** `DatedEvent.startYear` is
   null and the UI renders "no date in this scheme". It must never fall back
   to another scheme's number.

## Signing

Sideloaded releases must use the **same key every time**, or existing installs
cannot update and users lose their notes. Generate it once, back it up
somewhere safe, never regenerate. Android treats a differently-signed APK as a
different app.
