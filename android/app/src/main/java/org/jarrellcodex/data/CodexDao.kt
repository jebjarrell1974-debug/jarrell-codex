package org.jarrellcodex.data

import android.content.Context
import android.database.Cursor

/**
 * Every query here was written and benchmarked against the real database by
 * scripts/15_queries.py before being ported. Slowest measured was 24.8 ms
 * scanning all 682,818 morphemes; a chapter opens in under 2 ms.
 *
 * The SQL is the tested artifact and is kept verbatim. Only the cursor
 * plumbing is new.
 */
class CodexDao(context: Context) {

    private val db = CodexDatabase.open(context)

    private fun <T> query(sql: String, vararg args: String, map: (Cursor) -> T): List<T> {
        val out = ArrayList<T>()
        db.rawQuery(sql, args).use { c -> while (c.moveToNext()) out.add(map(c)) }
        return out
    }

    private fun Cursor.str(name: String): String? =
        getColumnIndex(name).let { if (it < 0 || isNull(it)) null else getString(it) }

    private fun Cursor.int(name: String): Int? =
        getColumnIndex(name).let { if (it < 0 || isNull(it)) null else getInt(it) }

    private fun Cursor.dbl(name: String): Double? =
        getColumnIndex(name).let { if (it < 0 || isNull(it)) null else getDouble(it) }

    fun chapter(book: String, chapter: Int) = query(
        """SELECT t.token_id, t.verse_key, t.position, t.surface, t.translit,
                  t.gloss, t.language
           FROM token t JOIN verse v ON v.verse_key = t.verse_key
           WHERE v.book = ? AND v.chapter = ?
             AND (t.text_type GLOB 'L*' OR t.text_type GLOB '*N*')
           ORDER BY v.verse, t.position""",
        book, chapter.toString(),
    ) { c ->
        Token(
            tokenId = c.str("token_id")!!, verseKey = c.str("verse_key")!!,
            position = c.int("position") ?: 0, surface = c.str("surface") ?: "",
            translit = c.str("translit"), gloss = c.str("gloss"),
            language = c.str("language") ?: "H",
        )
    }

    fun morphemes(tokenId: String) = query(
        """SELECT m.seq, m.surface, m.strongs, m.strongs_simple,
                  mc.description AS parsing, l.lemma, l.gloss, l.definition
           FROM morpheme m
           LEFT JOIN morph_code mc ON mc.code = m.morph_code
           LEFT JOIN lexicon    l  ON l.strongs = m.strongs
           WHERE m.token_id = ? ORDER BY m.seq""",
        tokenId,
    ) { c ->
        Morpheme(
            seq = c.int("seq") ?: 0, surface = c.str("surface"),
            strongs = c.str("strongs"), strongsSimple = c.str("strongs_simple"),
            parsing = c.str("parsing"), lemma = c.str("lemma"),
            gloss = c.str("gloss"), definition = c.str("definition"),
        )
    }

    fun translations(verseKey: String) = query(
        "SELECT code, text FROM translation_verse WHERE canonical_key = ? ORDER BY code",
        verseKey,
    ) { c -> VerseText(c.str("code") ?: "", c.str("text") ?: "") }

    /**
     * Concordance by SIMPLE Strong's. A reader holding a printed concordance
     * types "H3068", not the disambiguated "H3068G" - searching the extended
     * number alone returns nothing for them. Verified: H3068 finds 6,528.
     */
    fun concordance(simple: String, limit: Int, offset: Int) = query(
        """SELECT v.book, v.chapter, v.verse, t.verse_key, t.surface, t.gloss, m.strongs
           FROM morpheme m
           JOIN token t ON t.token_id = m.token_id
           JOIN verse v ON v.verse_key = t.verse_key
           WHERE m.strongs_simple = ?
           ORDER BY v.book_order, v.chapter, v.verse, t.position
           LIMIT ? OFFSET ?""",
        simple, limit.toString(), offset.toString(),
    ) { c ->
        ConcordanceRow(
            book = c.str("book") ?: "", chapter = c.int("chapter") ?: 0,
            verse = c.int("verse") ?: 0, verseKey = c.str("verse_key") ?: "",
            surface = c.str("surface") ?: "", gloss = c.str("gloss"),
            strongs = c.str("strongs"),
        )
    }

    fun concordanceCount(simple: String): Int =
        db.rawQuery("SELECT COUNT(*) FROM morpheme WHERE strongs_simple = ?", arrayOf(simple))
            .use { if (it.moveToFirst()) it.getInt(0) else 0 }

    fun places(verseKey: String) = query(
        """SELECT p.name, p.status, p.latitude, p.longitude, p.modern_name
           FROM place p JOIN place_verse pv ON pv.place_id = p.place_id
           WHERE pv.verse_key = ? ORDER BY p.name""",
        verseKey,
    ) { c ->
        Place(
            name = c.str("name") ?: "", status = c.str("status") ?: "unknown",
            latitude = c.dbl("latitude"), longitude = c.dbl("longitude"),
            modernName = c.str("modern_name"),
        )
    }

    fun people(verseKey: String) = query(
        """SELECT p.person_id, p.name, p.birth_year, p.death_year
           FROM person p JOIN person_verse pv ON pv.person_id = p.person_id
           WHERE pv.verse_key = ? ORDER BY p.name""",
        verseKey,
    ) { c ->
        Person(
            personId = c.int("person_id") ?: 0, name = c.str("name") ?: "",
            birthYear = c.int("birth_year"), deathYear = c.int("death_year"),
        )
    }

    /**
     * LEFT JOIN on purpose. A scheme with no date for this event yields a null
     * startYear, which the UI renders as "no date in this scheme". It must
     * never fall back to another scheme's number.
     */
    fun events(verseKey: String, schemeId: String) = query(
        """SELECT e.event_id, e.title, d.start_year, d.precision, d.note
           FROM event e
           JOIN event_verse ev ON ev.event_id = e.event_id
           LEFT JOIN event_date d
                  ON d.event_id = e.event_id AND d.scheme_id = ?
           WHERE ev.verse_key = ? ORDER BY e.sort_key""",
        schemeId, verseKey,
    ) { c ->
        DatedEvent(
            eventId = c.int("event_id") ?: 0, title = c.str("title") ?: "",
            startYear = c.int("start_year"), precision = c.str("precision"),
            note = c.str("note"),
        )
    }

    fun schemes() = query(
        """SELECT scheme_id, name, coverage, summary, source, is_default
           FROM chronology_scheme ORDER BY sort_order""",
    ) { c ->
        Scheme(
            schemeId = c.str("scheme_id") ?: "", name = c.str("name") ?: "",
            coverage = c.str("coverage") ?: "none", summary = c.str("summary") ?: "",
            source = c.str("source") ?: "", isDefault = (c.int("is_default") ?: 0) == 1,
        )
    }

    fun chronologyNotes() = query(
        "SELECT heading, body FROM chronology_note ORDER BY sort_order",
    ) { c -> ChronologyNote(c.str("heading") ?: "", c.str("body") ?: "") }

    fun tokenCount(): Int =
        db.rawQuery("SELECT COUNT(*) FROM token", null)
            .use { if (it.moveToFirst()) it.getInt(0) else 0 }
}

data class ConcordanceRow(
    val book: String, val chapter: Int, val verse: Int,
    val verseKey: String, val surface: String, val gloss: String?, val strongs: String?,
)
