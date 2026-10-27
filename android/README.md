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

## Releasing: the signing key is a one-way door

Android identifies an app by the key that signed it. Every update has to be
signed with the **same** key, or a phone refuses to install it over the copy
already there — the reader has to delete the app and lose whatever is in it.
There is no way to change the key afterwards, and nobody can issue you a new
one, because the key *is* the identity.

So this repository does not contain a key, and nothing here will create one
without being asked. A release build with no key present comes out unsigned
rather than failing, so anyone can still build and read the code.

To create the key, once and for good:

    ./make-release-key.sh "a long passphrase you will not lose"
    make-release-key.bat "a long passphrase you will not lose"

That writes `release.jks` (RSA 4096, thirty years' validity) and
`keystore.properties` beside the script. Both are gitignored, and both must
stay that way: anyone holding them can publish an update that Android will
install straight over a reader's copy.

**Back both files up immediately, somewhere that is not the machine that
made them.** Losing them means no future version of this app can ever be
installed over the one people already have. That is the whole of the risk,
and it is why this step is left to a person rather than done automatically.

With the key in place:

    gradle :app:assembleRelease     # an APK, for sideloading
    gradle :app:bundleRelease       # an .aab, for Google Play

A plain APK is capped at 100 MB on Play, and this one is 247 MB, so the Play
build has to be the bundle. Sideloading has no limit.

## What ships inside the app, and what does not

Inside, and therefore working with no signal at all: the Hebrew, Aramaic and
Greek with every word parsed, four English translations, the lexicons, the
places, the people, the events, the dictionary, the cross-references, the
translators' notes, 307 photographs of places and 150 of Doré's engravings.
Optionally the six commentaries, unpacked on request.

Not inside: the spoken readings. Those are public-domain LibriVox recordings
and amount to 2.5 GB, which would treble the download, so they stream from
archive.org. That is the only reason this app asks for INTERNET, and the only
thing in it that stops working when the signal does. Every screen that offers
a reading says so.
