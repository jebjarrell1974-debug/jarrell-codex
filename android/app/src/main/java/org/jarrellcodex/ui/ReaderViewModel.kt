package org.jarrellcodex.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import org.jarrellcodex.data.*

data class ReaderState(
    val loading: Boolean = true,
    val book: String = "Gen",
    val chapter: Int = 1,
    val verses: List<VerseBlock> = emptyList(),
    val selected: WordStudy? = null,
    val context: VerseContext? = null,
    val books: List<BookRef> = emptyList(),
    val picking: Boolean = false,          // the book list is open
    val pickingChaptersFor: BookRef? = null,
    val schemes: List<Scheme> = emptyList(),
    val schemeId: String = "jones",
    val error: String? = null,
    // the commentators, which the reader opts into
    val commentaryReady: Boolean = false,
    val commentaryOffered: Boolean = false,
    val unpacking: Boolean = false,
    val unpackProgress: Float = 0f,
    val commentaryCounts: Map<Int, Int> = emptyMap(),
    val noteCounts: Map<Int, Int> = emptyMap(),
    val xrefCounts: Map<Int, Int> = emptyMap(),
    // one sheet at a time, so one nullable each
    val notes: List<TranslationNote>? = null,
    val xrefs: List<CrossRef>? = null,
    val sheetTitle: String = "",
    val showAbout: Boolean = false,
    val translations: List<TranslationInfo> = emptyList(),
    val chronologyNotes: List<ChronologyNote> = emptyList(),
    val searching: Boolean = false,
    val query: String = "",
    val searchMode: SearchMode = SearchMode.Verses,
    val searchRunning: Boolean = false,
    val hitsVerses: List<SearchHit> = emptyList(),
    val hitsNotes: List<SearchHit> = emptyList(),
    val hitsWords: List<LexHit> = emptyList(),
    val commentary: List<CommentaryUnit>? = null,
    val commentaryTitle: String = "",
    // kept apart from `error`, which replaces the whole screen. Failing to
    // unpack an optional extra must not take the Bible away from the reader.
    val commentaryError: String? = null,
)

class ReaderViewModel(app: Application) : AndroidViewModel(app) {
    private val repo = CodexRepository(app)
    private val _state = MutableStateFlow(ReaderState())
    val state: StateFlow<ReaderState> = _state.asStateFlow()

    init { open("Gen", 1) }

    fun open(book: String, chapter: Int) = viewModelScope.launch {
        _state.value = _state.value.copy(loading = true, error = null, selected = null, context = null)
        runCatching {
            val schemes = repo.schemes()
            val books = if (_state.value.books.isEmpty()) repo.books() else _state.value.books
            val default = schemes.firstOrNull { it.isDefault }?.schemeId ?: "jones"
            val verses = repo.chapter(book, chapter)
            val ready = repo.hasCommentary()
            val marks = repo.markers(book, chapter)
            _state.value = _state.value.copy(
                loading = false, book = book, chapter = chapter,
                verses = verses, schemes = schemes, books = books,
                picking = false, pickingChaptersFor = null,
                schemeId = _state.value.schemeId.takeIf { s -> schemes.any { it.schemeId == s } } ?: default,
                commentaryReady = ready,
                commentaryOffered = !ready && repo.commentaryAvailable(),
                commentaryCounts = marks.first,
                noteCounts = marks.second,
                xrefCounts = marks.third,
            )
        }.onFailure { e ->
            _state.value = _state.value.copy(loading = false, error = e.message ?: "Could not open the text")
        }
    }

    // ---- searching --------------------------------------------------------

    private var searchJob: Job? = null

    fun openSearch() { _state.value = _state.value.copy(searching = true) }
    fun closeSearch() {
        searchJob?.cancel()
        _state.value = _state.value.copy(searching = false, searchRunning = false)
    }
    fun setMode(m: SearchMode) {
        _state.value = _state.value.copy(searchMode = m)
        runSearch(_state.value.query)
    }

    /**
     * Debounced, and the previous search is cancelled before a new one starts.
     * Typing "covenant" would otherwise fire eight searches and let whichever
     * finished last win, which is not necessarily the one matching what is on
     * screen.
     */
    fun setQuery(q: String) {
        _state.value = _state.value.copy(query = q)
        runSearch(q)
    }

    private fun runSearch(q: String) {
        searchJob?.cancel()
        if (q.isBlank()) {
            _state.value = _state.value.copy(
                searchRunning = false, hitsVerses = emptyList(),
                hitsNotes = emptyList(), hitsWords = emptyList(),
            )
            return
        }
        searchJob = viewModelScope.launch {
            delay(250)
            _state.value = _state.value.copy(searchRunning = true)
            when (_state.value.searchMode) {
                SearchMode.Verses ->
                    _state.value = _state.value.copy(hitsVerses = repo.searchVerses(q))
                SearchMode.Notes ->
                    _state.value = _state.value.copy(hitsNotes = repo.searchNotes(q))
                SearchMode.Words ->
                    _state.value = _state.value.copy(hitsWords = repo.searchLexicon(q))
            }
            _state.value = _state.value.copy(searchRunning = false)
        }
    }

    /** Jumping from a search result should leave the search behind. */
    fun goToFromSearch(verseKey: String) {
        closeSearch()
        goTo(verseKey)
    }

    // ---- the context layers ----------------------------------------------

    fun openNotes(verseKey: String) = viewModelScope.launch {
        _state.value = _state.value.copy(
            notes = repo.notes(verseKey),
            sheetTitle = "Notes on " + verseKey.replace('.', ' '),
        )
    }

    fun openXrefs(verseKey: String) = viewModelScope.launch {
        _state.value = _state.value.copy(
            xrefs = repo.xrefs(verseKey),
            sheetTitle = "Cross-references from " + verseKey.replace('.', ' '),
        )
    }

    fun closeContext() {
        _state.value = _state.value.copy(notes = null, xrefs = null)
    }

    /** A cross-reference is only useful if tapping it takes you there. */
    fun goTo(verseKey: String) {
        val p = verseKey.split('.')
        if (p.size >= 2) {
            closeContext()
            open(p[0], p[1].toIntOrNull() ?: 1)
        }
    }

    fun openAbout() = viewModelScope.launch {
        _state.value = _state.value.copy(
            showAbout = true,
            translations = if (_state.value.translations.isEmpty()) repo.translations()
                           else _state.value.translations,
            chronologyNotes = if (_state.value.chronologyNotes.isEmpty()) repo.chronologyNotes()
                              else _state.value.chronologyNotes,
        )
    }

    fun closeAbout() { _state.value = _state.value.copy(showAbout = false) }

    // ---- moving around the text -----------------------------------------

    fun openPicker() { _state.value = _state.value.copy(picking = true, pickingChaptersFor = null) }
    fun pickBook(b: BookRef) { _state.value = _state.value.copy(pickingChaptersFor = b) }
    fun closePicker() { _state.value = _state.value.copy(picking = false, pickingChaptersFor = null) }

    /** Steps past the end of a book into the next one, the way a reader expects. */
    fun step(delta: Int) {
        val s = _state.value
        val here = s.books.indexOfFirst { it.code == s.book }
        if (here < 0) return
        val next = s.chapter + delta
        when {
            next in 1..s.books[here].chapters -> open(s.book, next)
            next < 1 && here > 0 -> s.books[here - 1].let { open(it.code, it.chapters) }
            next > s.books[here].chapters && here < s.books.lastIndex ->
                open(s.books[here + 1].code, 1)
            // first chapter of Genesis or last of Revelation: nowhere to go
        }
    }

    /** Null at the ends of the canon, so the UI can hide the button. */
    fun neighbour(delta: Int): Pair<String, Int>? {
        val s = _state.value
        val here = s.books.indexOfFirst { it.code == s.book }
        if (here < 0) return null
        val next = s.chapter + delta
        return when {
            next in 1..s.books[here].chapters -> s.book to next
            next < 1 && here > 0 -> s.books[here - 1].let { it.code to it.chapters }
            next > s.books[here].chapters && here < s.books.lastIndex ->
                s.books[here + 1].code to 1
            else -> null
        }
    }

    fun bookName(code: String): String =
        _state.value.books.firstOrNull { it.code == code }?.name ?: code

    fun selectWord(token: Token) = viewModelScope.launch {
        val study = repo.wordStudy(token)
        val ctx = repo.context(token.verseKey, _state.value.schemeId)
        _state.value = _state.value.copy(selected = study, context = ctx)
    }

    fun clearSelection() { _state.value = _state.value.copy(selected = null, context = null) }

    // ---- the commentators ------------------------------------------------

    fun openCommentary(verseKey: String) = viewModelScope.launch {
        val units = repo.commentaryOn(verseKey)
        _state.value = _state.value.copy(
            commentary = units,
            commentaryTitle = "Commentary on " + verseKey.replace('.', ' '),
        )
    }

    fun openChapterCommentary() = viewModelScope.launch {
        val s = _state.value
        val units = repo.commentaryOnChapter(s.book, s.chapter)
        _state.value = _state.value.copy(
            commentary = units,
            commentaryTitle = "On ${s.book} ${s.chapter} as a whole",
        )
    }

    fun closeCommentary() { _state.value = _state.value.copy(commentary = null) }

    /**
     * Unpacking 148 MB takes a while. Progress is reported so the wait does
     * not look like a hang, and a failure leaves the app exactly as it was
     * rather than half-enabled.
     */
    fun addCommentary() = viewModelScope.launch {
        _state.value = _state.value.copy(unpacking = true, unpackProgress = 0f)
        val ok = repo.addCommentary { p ->
            _state.value = _state.value.copy(unpackProgress = p)
        }
        val s = _state.value
        _state.value = s.copy(
            unpacking = false,
            commentaryReady = ok,
            commentaryOffered = !ok,
            commentaryCounts = if (ok) repo.commentaryCounts(s.book, s.chapter) else emptyMap(),
            commentaryError = if (ok) null
                else "The commentaries could not be unpacked \u2014 there may not " +
                     "be enough room on this phone. Everything else still works.",
        )
    }

    fun removeCommentary() = viewModelScope.launch {
        repo.removeCommentary()
        _state.value = _state.value.copy(
            commentaryReady = false,
            commentaryOffered = repo.commentaryAvailable(),
            commentaryCounts = emptyMap(),
            commentary = null,
        )
    }

    fun chooseScheme(schemeId: String) = viewModelScope.launch {
        val key = _state.value.selected?.token?.verseKey
        val ctx = key?.let { repo.context(it, schemeId) }
        _state.value = _state.value.copy(schemeId = schemeId, context = ctx ?: _state.value.context)
    }
}
