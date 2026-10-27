# Jarrell Codex — Android client

Kotlin + Jetpack Compose. Reads the prebuilt database from `scripts/build_all.sh`.

## ⚠️ This project has never been compiled

It was written in an environment with no Android SDK and no access to
`dl.google.com` or Maven Central, so **nothing here has been built, run, or
tested on a device.** The SQL inside it *has* been tested — every query in
`CodexDao` was written and benchmarked against the real database by
`scripts/15_queries.py` before being ported — but the Kotlin, the Gradle
config and the Compose UI are unverified.

Expect to fix things on first build. Likely candidates:

- **Dependency versions** in `gradle/libs.versions.toml` were not resolved by
  a real Gradle run. Check them first.
- **Room's compile-time verification.** Room checks every `@Query` against the
  schema it knows. The schema here is prebuilt and only one entity is declared,
  so Room may object to columns it cannot see. If it does, the fix is to
  declare the remaining tables as `@Entity` classes (tedious but mechanical),
  or to drop Room and use `SQLiteDatabase` directly with the same SQL.
- The Gradle wrapper is **not** included. Run `gradle wrapper` once.

## How the database ships

Prebuilt, read-only, gzipped in `app/src/main/assets/codex.db.gz` at 61 MB,
expanded by Room to about 226 MB in app storage on first launch.

Google Play's limit for a base module is 500 MB compressed, so the whole
database fits with no asset pack and no first-run download. That is the point:
the app works the moment it is installed, with no signal and no account.

## What the UI is a port of

A working reference reader was built and tested against the same data first, so
the Compose screens are a port of something known-good rather than a guess at
the interaction. Three behaviours are load-bearing and should not be
"simplified" away:

1. **Tapping a word shows its morphemes, not just the word.** One printed
   Hebrew word can hold a prefix, root and suffix with separate Strong's
   numbers. `בְּרֵאשִׁית` is `H9003` *in* + `H7225G` *beginning*.
2. **The concordance searches simple Strong's.** A reader with a printed
   concordance types `H3068`, not the disambiguated `H3068G`. Searching the
   extended number alone finds nothing for them.
3. **A chronology scheme with no date says so.** `DatedEvent.startYear` is
   null and the UI renders "no date in this scheme". It must never fall back
   to another scheme's number.

## Signing

Sideloaded releases must use the **same key every time**, or existing installs
cannot update and users lose their notes. Generate it once, back it up
somewhere safe, never regenerate. Android treats a differently-signed APK as a
different app.
