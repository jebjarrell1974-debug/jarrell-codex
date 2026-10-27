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

    /**
     * The translators' notes on a verse - what the original actually says,
     * where the idiom will not carry, what a reader in that culture would
     * have heard. The "cultural context" layer, verse by verse.
     */
    fun notes(verseKey: String) = query(
        """SELECT quote, category, body, source FROM note
           WHERE verse_key = ? ORDER BY note_id""",
        verseKey,
    ) { c ->
        TranslationNote(
            quote = c.str("quote"), category = c.str("category"),
            body = c.str("body") ?: "", source = c.str("source") ?: "",
        )
    }

    fun noteCounts(book: String, chapter: Int): Map<Int, Int> {
        val out = HashMap<Int, Int>()
        db.rawQuery(
            "SELECT verse, COUNT(*) FROM note WHERE book = ? AND chapter = ? GROUP BY verse",
            arrayOf(book, chapter.toString()),
        ).use { c -> while (c.moveToNext()) out[c.getInt(0)] = c.getInt(1) }
        return out
    }

    /**
     * Cross-references, heaviest first. The vote is how strongly editors and
     * readers have linked the two passages - a weight, not a certainty, and
     * the UI says so.
     */
    fun xrefs(verseKey: String, limit: Int = 60) = query(
        """SELECT to_key, to_end_key, votes FROM xref
           WHERE from_key = ? ORDER BY votes DESC LIMIT ?""",
        verseKey, limit.toString(),
    ) { c ->
        CrossRef(
            toKey = c.str("to_key") ?: "", toEndKey = c.str("to_end_key"),
            votes = c.int("votes") ?: 0,
        )
    }

    fun xrefCounts(book: String, chapter: Int): Map<Int, Int> {
        val out = HashMap<Int, Int>()
        db.rawQuery(
            """SELECT v.verse, COUNT(*) FROM xref x
               JOIN verse v ON v.verse_key = x.from_key
               WHERE v.book = ? AND v.chapter = ? GROUP BY v.verse""",
            arrayOf(book, chapter.toString()),
        ).use { c -> while (c.moveToNext()) out[c.getInt(0)] = c.getInt(1) }
        return out
    }

    /**
     * Full-text search over the English verses, built as FTS4 at database
     * time, so this is an index hit rather than a scan. Benchmarked under
     * 400 ms for the worst query in scripts/19_search.py.
     *
     * FTS treats several characters as operators. A reader typing an
     * apostrophe or a hyphen means them literally, so the term is quoted and
     * any embedded quote stripped - otherwise "Jacob's" is a syntax error
     * thrown at somebody looking for Jacob.
     */
    fun searchVerses(q: String, limit: Int = 200) = query(
        """SELECT s.verse_key, s.code, s.text
           FROM search_verse s JOIN verse v ON v.verse_key = s.verse_key
           WHERE search_verse MATCH ? AND s.code = 'KJV'
           ORDER BY v.book_order, v.chapter, v.verse LIMIT ?""",
        ftsQuery(q), limit.toString(),
    ) { c ->
        SearchHit(
            verseKey = c.str("verse_key") ?: "",
            text = c.str("text") ?: "",
        )
    }

    /** The same over the translators' notes. */
    fun searchNotes(q: String, limit: Int = 200) = query(
        """SELECT n.verse_key, substr(n.body, 1, 180) AS text
           FROM search_note s
           JOIN note n ON n.note_id = s.note_id
           JOIN verse v ON v.verse_key = n.verse_key
           WHERE search_note MATCH ?
           ORDER BY v.book_order, v.chapter, v.verse LIMIT ?""",
        ftsQuery(q), limit.toString(),
    ) { c ->
        SearchHit(
            verseKey = c.str("verse_key") ?: "",
            text = (c.str("text") ?: "").replace("**", ""),
        )
    }

    /**
     * English meaning to original word: "shepherd" -> poimen.
     *
     * FTS4 matches any column and has no relevance ranking, so an unordered
     * search for "shepherd" answers with the Hebrew for "idol" - the word
     * appears somewhere in its definition. Words whose own gloss or lemma is
     * the thing being searched for come first, shortest gloss before longest,
     * which puts the actual shepherd words at the top where they belong.
     */
    fun searchLexicon(q: String, limit: Int = 60): List<LexHit> {
        val like = "%" + q.trim().lowercase() + "%"
        return query(
            """SELECT strongs, lemma, gloss,
                      CASE WHEN lower(gloss) LIKE ? THEN 0
                           WHEN lower(lemma) LIKE ? THEN 1
                           ELSE 2 END AS rank
               FROM search_lexicon
               WHERE search_lexicon MATCH ?
               ORDER BY rank, length(gloss) LIMIT ?""",
            like, like, ftsQuery(q), limit.toString(),
        ) { c ->
            LexHit(
                strongs = c.str("strongs") ?: "", lemma = c.str("lemma") ?: "",
                gloss = c.str("gloss") ?: "",
            )
        }
    }

    /** What the About screen has to show: CC BY means attribution travels. */
    fun translations() = query(
        "SELECT code, name, licence FROM translation ORDER BY code",
    ) { c ->
        TranslationInfo(c.str("code") ?: "", c.str("name") ?: "", c.str("licence") ?: "")
    }

    /**
     * Every book with its chapter count and the names a reader might type.
     * book_name carries the full name and the usual abbreviations; without
     * this the app can open Genesis 1 and nothing else.
     */
    fun books() = query(
        """SELECT v.book, v.book_order, v.testament, MAX(v.chapter) AS chapters,
                  (SELECT b.name FROM book_name b
                    WHERE b.book = v.book AND b.kind = 'full'
                    ORDER BY b.rowid LIMIT 1) AS full_name
           FROM verse v GROUP BY v.book, v.book_order, v.testament
           ORDER BY v.book_order""",
    ) { c ->
        BookRef(
            code = c.str("book") ?: "",
            order = c.int("book_order") ?: 0,
            testament = c.str("testament") ?: "OT",
            chapters = c.int("chapters") ?: 1,
            // Job has no 'full' row - the source lists no separate full name
            // for a book already called Job - so fall back to the code rather
            // than rendering an empty title.
            name = c.str("full_name") ?: c.str("book") ?: "",
        )
    }

    fun tokenCount(): Int =
        db.rawQuery("SELECT COUNT(*) FROM token", null)
            .use { if (it.moveToFirst()) it.getInt(0) else 0 }
}

data class SearchHit(val verseKey: String, val text: String) {
    val book: String get() = verseKey.substringBefore('.')
    fun label(name: String): String {
        val p = verseKey.split('.')
        return if (p.size >= 3) "$name ${p[1]}:${p[2]}" else name
    }
}

data class LexHit(val strongs: String, val lemma: String, val gloss: String)

/**
 * Make a reader's words safe for FTS. Quoting each term keeps apostrophes,
 * hyphens and stray operators literal; two or more terms become a phrase
 * requirement, which is what people expect when they type several words.
 */
internal fun ftsQuery(raw: String): String =
    raw.trim().split(Regex("\\s+"))
        .filter { it.isNotBlank() }
        .joinToString(" ") { "\"" + it.replace("\"", "") + "\"" }
        .ifBlank { "\"\"" }

data class TranslationNote(
    val quote: String?,
    val category: String?,
    val body: String,
    val source: String,
)

data class CrossRef(val toKey: String, val toEndKey: String?, val votes: Int) {
    val book: String get() = toKey.substringBefore('.')

    /**
     * "Rom.5.8" with a display name -> "Romans 5:8"; a range that stays in
     * the same chapter collapses to "Romans 5:8-10" rather than repeating it.
     * The name is passed in because only the UI knows how a book is spelled.
     */
    fun label(name: String): String {
        val p = toKey.split('.')
        if (p.size < 3) return name
        val base = "$name ${p[1]}:${p[2]}"
        val e = toEndKey?.split('.') ?: return base
        if (e.size < 3) return base
        return if (e[1] == p[1]) "$base-${e[2]}" else "$base \u2013 ${e[1]}:${e[2]}"
    }
}

data class TranslationInfo(val code: String, val name: String, val licence: String)

data class BookRef(
    val code: String,
    val order: Int,
    val testament: String,       // OT | NT
    val chapters: Int,
    val name: String,
)

data class ConcordanceRow(
    val book: String, val chapter: Int, val verse: Int,
    val verseKey: String, val surface: String, val gloss: String?, val strongs: String?,
)
