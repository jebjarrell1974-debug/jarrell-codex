package org.jarrellcodex.data

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class CodexRepository(context: Context) {
    private val dao = CodexDatabase.get(context).dao()

    /** First call blocks while Room expands the 226 MB database. Call it off the main thread. */
    suspend fun warmUp(): Int = withContext(Dispatchers.IO) { dao.tokenCount() }

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

    suspend fun context(verseKey: String, schemeId: String) = withContext(Dispatchers.IO) {
        VerseContext(
            places = dao.places(verseKey),
            people = dao.people(verseKey),
            events = dao.events(verseKey, schemeId),
        )
    }

    suspend fun schemes(): List<Scheme> = withContext(Dispatchers.IO) { dao.schemes() }
    suspend fun chronologyNotes(): List<ChronologyNote> = withContext(Dispatchers.IO) { dao.chronologyNotes() }

    suspend fun concordance(simple: String, page: Int, pageSize: Int = 50) =
        withContext(Dispatchers.IO) { dao.concordance(simple, pageSize, page * pageSize) }
}

data class VerseBlock(val verseKey: String, val tokens: List<Token>, val translations: List<VerseText>) {
    val number: String get() = verseKey.substringAfterLast('.')
    val isRtl: Boolean get() = tokens.firstOrNull()?.isRtl == true
}
data class WordStudy(val token: Token, val morphemes: List<Morpheme>, val counts: Map<String, Int>)
data class VerseContext(val places: List<Place>, val people: List<Person>, val events: List<DatedEvent>)
