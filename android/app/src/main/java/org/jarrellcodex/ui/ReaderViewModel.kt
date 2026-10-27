package org.jarrellcodex.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import org.jarrellcodex.data.*

data class ReaderState(
    val loading: Boolean = true,
    val book: String = "Gen",
    val chapter: Int = 1,
    val verses: List<VerseBlock> = emptyList(),
    val selected: WordStudy? = null,
    val context: VerseContext? = null,
    val schemes: List<Scheme> = emptyList(),
    val schemeId: String = "jones",
    val error: String? = null,
    // the commentators, which the reader opts into
    val commentaryReady: Boolean = false,
    val commentaryOffered: Boolean = false,
    val unpacking: Boolean = false,
    val unpackProgress: Float = 0f,
    val commentaryCounts: Map<Int, Int> = emptyMap(),
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
            val default = schemes.firstOrNull { it.isDefault }?.schemeId ?: "jones"
            val verses = repo.chapter(book, chapter)
            val ready = repo.hasCommentary()
            _state.value = _state.value.copy(
                loading = false, book = book, chapter = chapter,
                verses = verses, schemes = schemes,
                schemeId = _state.value.schemeId.takeIf { s -> schemes.any { it.schemeId == s } } ?: default,
                commentaryReady = ready,
                commentaryOffered = !ready && repo.commentaryAvailable(),
                commentaryCounts = if (ready) repo.commentaryCounts(book, chapter) else emptyMap(),
            )
        }.onFailure { e ->
            _state.value = _state.value.copy(loading = false, error = e.message ?: "Could not open the text")
        }
    }

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
