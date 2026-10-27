package org.jarrellcodex.data

import android.content.Context
import android.database.Cursor

/**
 * Reads the optional commentary database. Every method returns an empty list
 * when the reader has not added the commentators, so callers never have to
 * ask first.
 *
 * Queries were checked against the real file before porting: Jhn.3.16 returns
 * five units, one each from Henry, Geneva, Calvin, Poole and Trapp.
 */
class CommentaryDao(context: Context) {

    private val app = context.applicationContext
    private val db get() = CommentaryDatabase.openOrNull(app)

    val isReady: Boolean get() = db != null

    private fun <T> query(sql: String, vararg args: String, map: (Cursor) -> T): List<T> {
        val handle = db ?: return emptyList()
        val out = ArrayList<T>()
        handle.rawQuery(sql, args).use { c -> while (c.moveToNext()) out.add(map(c)) }
        return out
    }

    private fun Cursor.str(name: String): String? =
        getColumnIndex(name).let { if (it < 0 || isNull(it)) null else getString(it) }

    private fun Cursor.int(name: String): Int? =
        getColumnIndex(name).let { if (it < 0 || isNull(it)) null else getInt(it) }

    private fun unit(c: Cursor) = CommentaryUnit(
        unitId = c.int("unit_id") ?: 0,
        sourceId = c.str("source_id") ?: "",
        author = c.str("author") ?: "",
        work = c.str("work") ?: "",
        scope = c.str("scope") ?: "passage",
        verseFrom = c.int("verse_from"),
        verseTo = c.int("verse_to"),
        title = c.str("title"),
        body = c.str("body") ?: "",
    )

    /** Everything written on this one verse, in the commentators' own order. */
    fun forVerse(verseKey: String) = query(
        """SELECT c.unit_id, c.source_id, m.author, m.work, c.scope,
                  c.verse_from, c.verse_to, c.title, c.body
           FROM commentary_verse v
           JOIN commentary  c ON c.unit_id   = v.unit_id
           JOIN commentator m ON m.source_id = c.source_id
           WHERE v.verse_key = ?
           ORDER BY m.sort, c.verse_from""",
        verseKey,
    ) { unit(it) }

    /**
     * Prefaces to the book and overviews of the chapter - the units that cover
     * no single verse. Shown apart from the verse notes because they are a
     * different kind of thing.
     */
    fun forChapter(book: String, chapter: Int) = query(
        """SELECT c.unit_id, c.source_id, m.author, m.work, c.scope,
                  c.verse_from, c.verse_to, c.title, c.body
           FROM commentary c
           JOIN commentator m ON m.source_id = c.source_id
           WHERE c.book = ? AND c.chapter = ? AND c.verse_from IS NULL
           ORDER BY CASE c.scope WHEN 'book' THEN 0 ELSE 1 END, m.sort""",
        book, chapter.toString(),
    ) { unit(it) }

    /**
     * How many units touch each verse of a chapter, so the reader can mark a
     * verse without loading any text. Read straight off commentary's own
     * verse_from / verse_to rather than picking the number back out of
     * verse_key with string functions - the range is already stored, and one
     * small query beats one per verse.
     */
    fun countsForChapter(book: String, chapter: Int): Map<Int, Int> {
        val handle = db ?: return emptyMap()
        val out = HashMap<Int, Int>()
        handle.rawQuery(
            """SELECT verse_from, verse_to FROM commentary
               WHERE book = ? AND chapter = ? AND verse_from IS NOT NULL""",
            arrayOf(book, chapter.toString()),
        ).use { c ->
            while (c.moveToNext()) {
                val from = c.getInt(0)
                val to = if (c.isNull(1)) from else c.getInt(1)
                for (n in from..to) out[n] = (out[n] ?: 0) + 1
            }
        }
        return out
    }

    fun commentators() = query(
        "SELECT source_id, author, work, sort FROM commentator ORDER BY sort",
    ) { c ->
        Commentator(
            sourceId = c.str("source_id") ?: "", author = c.str("author") ?: "",
            work = c.str("work") ?: "", sort = c.int("sort") ?: 0,
        )
    }

    fun unitCount(): Int {
        val handle = db ?: return 0
        return handle.rawQuery("SELECT COUNT(*) FROM commentary", null)
            .use { if (it.moveToFirst()) it.getInt(0) else 0 }
    }
}
