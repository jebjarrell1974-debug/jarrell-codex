package org.jarrellcodex.data

import androidx.room.Dao
import androidx.room.Query

/**
 * Every query here was written and benchmarked against the real database by
 * scripts/15_queries.py before being ported. Slowest measured was 24.8 ms
 * scanning all 682,818 morphemes; a chapter opens in under 2 ms.
 */
@Dao
interface CodexDao {

    @Query("""SELECT t.token_id AS tokenId, t.verse_key AS verseKey, t.position,
                     t.surface, t.translit, t.gloss, t.language
              FROM token t JOIN verse v ON v.verse_key = t.verse_key
              WHERE v.book = :book AND v.chapter = :chapter
                AND (t.text_type GLOB 'L*' OR t.text_type GLOB '*N*')
              ORDER BY v.verse, t.position""")
    suspend fun chapter(book: String, chapter: Int): List<Token>

    @Query("""SELECT m.seq, m.surface, m.strongs, m.strongs_simple AS strongsSimple,
                     c.description AS parsing, l.lemma, l.gloss, l.definition
              FROM morpheme m
              LEFT JOIN morph_code c ON c.code = m.morph_code
              LEFT JOIN lexicon   l ON l.strongs = m.strongs
              WHERE m.token_id = :tokenId ORDER BY m.seq""")
    suspend fun morphemes(tokenId: String): List<Morpheme>

    @Query("SELECT code, text FROM translation_verse WHERE canonical_key = :verseKey ORDER BY code")
    suspend fun translations(verseKey: String): List<VerseText>

    /**
     * Concordance by SIMPLE Strong's. A reader holding a printed concordance
     * types "H3068", not the disambiguated "H3068G" - searching the extended
     * number alone returns nothing for them.
     */
    @Query("""SELECT v.book, v.chapter, v.verse, t.verse_key AS verseKey,
                     t.surface, t.gloss, m.strongs
              FROM morpheme m
              JOIN token t ON t.token_id = m.token_id
              JOIN verse v ON v.verse_key = t.verse_key
              WHERE m.strongs_simple = :simple
              ORDER BY v.book_order, v.chapter, v.verse, t.position
              LIMIT :limit OFFSET :offset""")
    suspend fun concordance(simple: String, limit: Int, offset: Int): List<ConcordanceRow>

    @Query("SELECT COUNT(*) FROM morpheme WHERE strongs_simple = :simple")
    suspend fun concordanceCount(simple: String): Int

    @Query("""SELECT p.name, p.status, p.latitude, p.longitude, p.modern_name AS modernName
              FROM place p JOIN place_verse pv ON pv.place_id = p.place_id
              WHERE pv.verse_key = :verseKey ORDER BY p.name""")
    suspend fun places(verseKey: String): List<Place>

    @Query("""SELECT p.person_id AS personId, p.name,
                     p.birth_year AS birthYear, p.death_year AS deathYear
              FROM person p JOIN person_verse pv ON pv.person_id = p.person_id
              WHERE pv.verse_key = :verseKey ORDER BY p.name""")
    suspend fun people(verseKey: String): List<Person>

    /**
     * LEFT JOIN on purpose. A scheme with no date for this event yields a null
     * startYear, which the UI renders as "no date in this scheme". It must
     * never fall back to another scheme's number.
     */
    @Query("""SELECT e.event_id AS eventId, e.title,
                     d.start_year AS startYear, d.precision, d.note
              FROM event e
              JOIN event_verse ev ON ev.event_id = e.event_id
              LEFT JOIN event_date d
                     ON d.event_id = e.event_id AND d.scheme_id = :schemeId
              WHERE ev.verse_key = :verseKey ORDER BY e.sort_key""")
    suspend fun events(verseKey: String, schemeId: String): List<DatedEvent>

    @Query("""SELECT scheme_id AS schemeId, name, coverage, summary, source,
                     is_default AS isDefault
              FROM chronology_scheme ORDER BY sort_order""")
    suspend fun schemes(): List<Scheme>

    @Query("SELECT heading, body FROM chronology_note ORDER BY sort_order")
    suspend fun chronologyNotes(): List<ChronologyNote>

    @Query("SELECT COUNT(*) FROM token")
    suspend fun tokenCount(): Int
}

data class ConcordanceRow(
    val book: String, val chapter: Int, val verse: Int,
    val verseKey: String, val surface: String, val gloss: String?, val strongs: String?,
)
