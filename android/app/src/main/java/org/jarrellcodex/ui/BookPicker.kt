package org.jarrellcodex.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import org.jarrellcodex.data.BookRef

/**
 * Getting from one place in the text to another.
 *
 * Without this the app opens Genesis 1 and the reader is stuck there, which
 * is not a Bible, it is a page of Genesis.
 */
@Composable
fun BookPicker(
    books: List<BookRef>,
    chaptersFor: BookRef?,
    onBook: (BookRef) -> Unit,
    onChapter: (BookRef, Int) -> Unit,
) {
    if (chaptersFor != null) {
        Column(Modifier.fillMaxWidth().padding(horizontal = 20.dp)
            .padding(bottom = 28.dp)) {
            Text(
                "${chaptersFor.name} — ${chaptersFor.chapters} chapters",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(Modifier.height(12.dp))
            LazyVerticalGrid(
                columns = GridCells.Adaptive(minSize = 56.dp),
                modifier = Modifier.heightIn(max = 460.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items((1..chaptersFor.chapters).toList()) { n ->
                    OutlinedButton(
                        onClick = { onChapter(chaptersFor, n) },
                        contentPadding = PaddingValues(4.dp),
                        modifier = Modifier.height(48.dp),
                    ) { Text("$n", textAlign = TextAlign.Center) }
                }
            }
        }
        return
    }

    Column(
        Modifier.fillMaxWidth().verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp).padding(bottom = 28.dp),
    ) {
        listOf("OT" to "Old Testament", "NT" to "New Testament").forEach { (t, label) ->
            val group = books.filter { it.testament == t }
            if (group.isEmpty()) return@forEach
            Text(
                label,
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 14.dp, bottom = 8.dp),
            )
            group.chunked(2).forEach { pair ->
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    pair.forEach { b ->
                        OutlinedButton(
                            onClick = { onBook(b) },
                            modifier = Modifier.weight(1f).heightIn(min = 48.dp),
                            contentPadding = PaddingValues(horizontal = 10.dp, vertical = 6.dp),
                        ) {
                            Row(
                                Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                Text(b.name, style = MaterialTheme.typography.bodyMedium)
                                Text(
                                    "${b.chapters}",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                        }
                    }
                    if (pair.size == 1) Spacer(Modifier.weight(1f))
                }
                Spacer(Modifier.height(8.dp))
            }
        }
    }
}

/** Steps to the next or previous chapter, carrying on across book boundaries. */
@Composable
fun ChapterStepper(
    prev: Pair<String, Int>?,
    next: Pair<String, Int>?,
    nameOf: (String) -> String,
    onStep: (Int) -> Unit,
) {
    Row(
        Modifier.fillMaxWidth().padding(vertical = 20.dp),
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        if (prev != null) {
            OutlinedButton(
                onClick = { onStep(-1) },
                modifier = Modifier.weight(1f).heightIn(min = 48.dp),
            ) { Text("← ${nameOf(prev.first)} ${prev.second}") }
        }
        if (next != null) {
            OutlinedButton(
                onClick = { onStep(1) },
                modifier = Modifier.weight(1f).heightIn(min = 48.dp),
            ) { Text("${nameOf(next.first)} ${next.second} →") }
        }
    }
}
