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
            _state.value = _state.value.copy(
                loading = false, book = book, chapter = chapter,
                verses = verses, schemes = schemes,
                schemeId = _state.value.schemeId.takeIf { s -> schemes.any { it.schemeId == s } } ?: default,
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

    fun chooseScheme(schemeId: String) = viewModelScope.launch {
        val key = _state.value.selected?.token?.verseKey
        val ctx = key?.let { repo.context(it, schemeId) }
        _state.value = _state.value.copy(schemeId = schemeId, context = ctx ?: _state.value.context)
    }
}
