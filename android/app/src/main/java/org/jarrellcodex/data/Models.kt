package org.jarrellcodex.data

/** Plain rows. Shapes match build/query-shapes.json from the data build. */
data class Token(
    val tokenId: String,
    val verseKey: String,
    val position: Int,
    val surface: String,
    val translit: String?,
    val gloss: String?,
    val language: String,          // "H" Hebrew, "A" Aramaic, "G" Greek
) { val isRtl get() = language == "H" || language == "A" }

data class Morpheme(
    val seq: Int,
    val surface: String?,
    val strongs: String?,          // extended, e.g. H3068G
    val strongsSimple: String?,    // what a printed concordance prints, e.g. H3068
    val parsing: String?,          // expanded from the morphology code
    val lemma: String?,
    val gloss: String?,
    val definition: String?,
)

data class VerseText(val code: String, val text: String)
data class Place(
    val name: String,
    val status: String,            // identified | disputed | region | unknown
    val latitude: Double?,
    val longitude: Double?,
    val modernName: String?,
) { val hasPin get() = latitude != null && longitude != null }

data class Person(val personId: Int, val name: String, val birthYear: Int?, val deathYear: Int?)

data class DatedEvent(
    val eventId: Int,
    val title: String,
    val startYear: Int?,           // null means this scheme has no date - say so
    val precision: String?,        // stated | derived | approximate
    val note: String?,
)

data class Scheme(
    val schemeId: String,
    val name: String,
    val coverage: String,          // full | anchors | none
    val summary: String,
    val source: String,
    val isDefault: Boolean,
)

data class ChronologyNote(val heading: String, val body: String)

/** Years are negative for BC. Never render a raw negative number to a reader. */
fun formatYear(year: Int?): String? =
    when {
        year == null -> null
        year < 0 -> "${-year} BC"
        else -> "AD $year"
    }
