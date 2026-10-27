package org.jarrellcodex.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import org.jarrellcodex.data.LexHit
import org.jarrellcodex.data.SearchHit

enum class SearchMode { Verses, Notes, Words }

/**
 * Searching without a server, because there is no server.
 *
 * The indexes are FTS4 tables built into the database, so this works on a
 * phone that has never had a signal.
 */
@Composable
fun SearchSheet(
    query: String,
    mode: SearchMode,
    running: Boolean,
    verses: List<SearchHit>,
    notes: List<SearchHit>,
    words: List<LexHit>,
    nameOf: (String) -> String,
    onQuery: (String) -> Unit,
    onMode: (SearchMode) -> Unit,
    onGo: (String) -> Unit,
    onWord: (String) -> Unit,
) {
    Column(
        Modifier.fillMaxWidth().verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp).padding(bottom = 28.dp),
    ) {
        OutlinedTextField(
            value = query,
            onValueChange = onQuery,
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            label = { Text("Search") },
            placeholder = { Text("a word, or a phrase") },
            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
            keyboardActions = KeyboardActions(onSearch = { }),
        )
        Spacer(Modifier.height(10.dp))
        Row(
            Modifier.horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            SearchMode.entries.forEach { m ->
                FilterChip(
                    selected = mode == m,
                    onClick = { onMode(m) },
                    label = {
                        Text(
                            when (m) {
                                SearchMode.Verses -> "Verses" + countOf(verses.size, running, mode == m)
                                SearchMode.Notes -> "Notes" + countOf(notes.size, running, mode == m)
                                SearchMode.Words -> "Original words" + countOf(words.size, running, mode == m)
                            },
                        )
                    },
                )
            }
        }
        Spacer(Modifier.height(6.dp))

        if (running) {
            LinearProgressIndicator(Modifier.fillMaxWidth().padding(vertical = 10.dp))
        }

        val empty = when (mode) {
            SearchMode.Verses -> verses.isEmpty()
            SearchMode.Notes -> notes.isEmpty()
            SearchMode.Words -> words.isEmpty()
        }
        if (!running && query.isNotBlank() && empty) {
            Text(
                "Nothing found for “$query”.",
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(vertical = 16.dp),
            )
        }

        run {
            when (mode) {
                SearchMode.Verses -> verses.forEach { h -> HitRow(h, nameOf, onGo) }
                SearchMode.Notes -> notes.forEach { h -> HitRow(h, nameOf, onGo) }
                SearchMode.Words -> words.forEach { w ->
                    TextButton(
                        onClick = { onWord(w.strongs) },
                        modifier = Modifier.fillMaxWidth(),
                        contentPadding = PaddingValues(vertical = 10.dp),
                    ) {
                        Column(Modifier.fillMaxWidth()) {
                            Row {
                                Text(w.strongs, style = MaterialTheme.typography.labelMedium,
                                     color = MaterialTheme.colorScheme.primary)
                                Spacer(Modifier.width(10.dp))
                                Text(w.lemma, fontSize = 17.sp)
                            }
                            Text(w.gloss, style = MaterialTheme.typography.bodySmall,
                                 color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
            }
        }
    }
}

private fun countOf(n: Int, running: Boolean, active: Boolean) =
    if (running && active) "" else if (n > 0) "  $n" else ""

@Composable
private fun HitRow(h: SearchHit, nameOf: (String) -> String, onGo: (String) -> Unit) {
    TextButton(
        onClick = { onGo(h.verseKey) },
        modifier = Modifier.fillMaxWidth(),
        contentPadding = PaddingValues(vertical = 10.dp),
    ) {
        Column(Modifier.fillMaxWidth()) {
            Text(h.label(nameOf(h.book)), fontWeight = FontWeight.SemiBold,
                 style = MaterialTheme.typography.labelMedium,
                 color = MaterialTheme.colorScheme.primary)
            Spacer(Modifier.height(3.dp))
            Text(h.text, style = MaterialTheme.typography.bodySmall,
                 color = MaterialTheme.colorScheme.onSurfaceVariant,
                 lineHeight = 18.sp, maxLines = 3)
        }
    }
}

