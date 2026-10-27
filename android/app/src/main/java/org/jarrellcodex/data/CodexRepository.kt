package org.jarrellcodex.data

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class CodexRepository(private val context: Context) {

    private val dao by lazy { CodexDao(context) }
    private val commentary by lazy { CommentaryDao(context) }

    /** First call blocks while the 456 MB database is expanded. Off the main thread. */
    suspend fun warmUp(): Int = withContext(Dispatchers.IO) { dao.tokenCount() }

    // ---- the commentators, which are optional -----------------------------

    /** False until the reader has spent the disk on them. */
    suspend fun hasCommentary(): Boolean = withContext(Dispatchers.IO) { commentary.isReady }

    /** True when the APK carries the asset at all. */
    fun commentaryAvailable(): Boolean = CommentaryDatabase.isAvailable(context)

    suspend fun addCommentary(onProgress: (Float) -> Unit): Boolean =
        withContext(Dispatchers.IO) { CommentaryDatabase.unpack(context, onProgress) }

    suspend fun removeCommentary(): Boolean =
        withContext(Dispatchers.IO) { CommentaryDatabase.remove(context) }

    suspend fun commentaryOn(verseKey: String): List<CommentaryUnit> =
        withContext(Dispatchers.IO) { commentary.forVerse(verseKey) }

    suspend fun commentaryOnChapter(book: String, chapter: Int): List<CommentaryUnit> =
        withContext(Dispatchers.IO) { commentary.forChapter(book, chapter) }

    /** Verse number -> how many units touch it, for the chapter markers. */
    suspend fun commentaryCounts(book: String, chapter: Int): Map<Int, Int> =
        withContext(Dispatchers.IO) { commentary.countsForChapter(book, chapter) }

    suspend fun chapter(book: String, chapter: Int): List<VerseBlock> = withContext(Dispatchers.IO) {
        dao.chapter(book, chapter)
            .groupBy { it.verseKey }
            .map { (key, tokens) -> VerseBlock(key, tokens, dao.translations(key)) }
    }

    suspend fun wordStudy(token: Token): WordStudy = withContext(Dispatchers.IO) {
        val parts = dao.morphemes(token.tokenId)
        WordStudy(
            token = token,
            morphemes = parts,
            counts = parts.mapNotNull { it.strongsSimple }
                .distinct()
                .associateWith { dao.concordanceCount(it) },
        )
    }

    suspend fun context(verseKey: String, schemeId: String): VerseContext = withContext(Dispatchers.IO) {
        VerseContext(
            places = dao.places(verseKey),
            people = dao.people(verseKey),
            events = dao.events(verseKey, schemeId),
        )
    }

    suspend fun books(): List<BookRef> = withContext(Dispatchers.IO) { dao.books() }

    suspend fun notes(verseKey: String): List<TranslationNote> =
        withContext(Dispatchers.IO) { dao.notes(verseKey) }

    suspend fun xrefs(verseKey: String): List<CrossRef> =
        withContext(Dispatchers.IO) { dao.xrefs(verseKey) }

    suspend fun searchVerses(q: String): List<SearchHit> =
        withContext(Dispatchers.IO) { runCatching { dao.searchVerses(q) }.getOrDefault(emptyList()) }

    suspend fun searchNotes(q: String): List<SearchHit> =
        withContext(Dispatchers.IO) { runCatching { dao.searchNotes(q) }.getOrDefault(emptyList()) }

    suspend fun searchLexicon(q: String): List<LexHit> =
        withContext(Dispatchers.IO) { runCatching { dao.searchLexicon(q) }.getOrDefault(emptyList()) }

    suspend fun translations(): List<TranslationInfo> =
        withContext(Dispatchers.IO) { dao.translations() }

    /** Verse -> count, for the markers under each verse. One query each. */
    suspend fun markers(book: String, chapter: Int): Triple<Map<Int, Int>, Map<Int, Int>, Map<Int, Int>> =
        withContext(Dispatchers.IO) {
            Triple(
                if (commentary.isReady) commentary.countsForChapter(book, chapter) else emptyMap(),
                dao.noteCounts(book, chapter),
                dao.xrefCounts(book, chapter),
            )
        }

    suspend fun timeline(schemeId: String): List<TimelineEntry> =
        withContext(Dispatchers.IO) { dao.timeline(schemeId) }

    suspend fun schemes(): List<Scheme> = withContext(Dispatchers.IO) { dao.schemes() }

    suspend fun chronologyNotes(): List<ChronologyNote> =
        withContext(Dispatchers.IO) { dao.chronologyNotes() }

    suspend fun concordance(simple: String, page: Int, pageSize: Int = 50): List<ConcordanceRow> =
        withContext(Dispatchers.IO) { dao.concordance(simple, pageSize, page * pageSize) }
}

data class VerseBlock(
    val verseKey: String,
    val tokens: List<Token>,
    val translations: List<VerseText>,
) {
    val number: String get() = verseKey.substringAfterLast('.')
    val isRtl: Boolean get() = tokens.firstOrNull()?.isRtl == true
}

data class WordStudy(val token: Token, val morphemes: List<Morpheme>, val counts: Map<String, Int>)
data class VerseContext(val places: List<Place>, val people: List<Person>, val events: List<DatedEvent>)
