package org.jarrellcodex.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.clickable
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import org.jarrellcodex.data.*

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun ReaderScreen(vm: ReaderViewModel) {
    val s by vm.state.collectAsState()

    if (s.loading && s.verses.isEmpty()) {
        Column(
            Modifier.fillMaxSize().padding(32.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            CircularProgressIndicator()
            Spacer(Modifier.height(20.dp))
            Text("Preparing the text", style = MaterialTheme.typography.titleMedium)
            Text(
                "Unpacking the Hebrew and Greek. This happens once.",
                style = MaterialTheme.typography.bodySmall,
                textAlign = TextAlign.Center,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        return
    }

    s.error?.let { msg ->
        Box(Modifier.fillMaxSize().padding(24.dp), Alignment.Center) { Text(msg) }
        return
    }

    Scaffold(topBar = {
        TopAppBar(
            title = {
                // The title is the way out of this chapter, so make it a button.
                TextButton(onClick = { vm.openPicker() }) {
                    Text(
                        "${vm.bookName(s.book)} ${s.chapter}",
                        style = MaterialTheme.typography.titleLarge,
                        color = MaterialTheme.colorScheme.onSurface,
                    )
                }
            },
            actions = {
                // The translation in use, and the way to change it. A code is
                // narrow enough for a phone's bar and is what a reader who
                // cares about the difference already recognises.
                TranslationPicker(
                    current = s.translationCode,
                    options = s.translations,
                    onPick = { vm.chooseTranslation(it) },
                    onNeedOptions = { vm.loadTranslations() },
                )
                // Text size and colours. Labelled in letters rather than a
                // glyph, because the control for making text readable should
                // not itself be the smallest thing in the bar.
                IconButton(onClick = { vm.openDisplay() }) {
                    Text("Aa", style = MaterialTheme.typography.titleMedium,
                         fontWeight = FontWeight.SemiBold)
                }
                IconButton(onClick = { vm.openTimeline() }) {
                    Text("\u29d6", style = MaterialTheme.typography.titleMedium)
                }
                IconButton(onClick = { vm.openSearch() }) {
                    Text("\u2315", style = MaterialTheme.typography.titleLarge)
                }
                IconButton(onClick = { vm.openAbout() }) {
                    Text("i", style = MaterialTheme.typography.titleMedium)
                }
            },
        )
    }) { pad ->
        LazyColumn(
            Modifier.fillMaxSize().padding(pad),
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
        ) {
            if (s.commentaryOffered) {
                item {
                    AddCommentaryCard(
                        unpacking = s.unpacking,
                        progress = s.unpackProgress,
                        failure = s.commentaryError,
                        onAdd = { vm.addCommentary() },
                    )
                }
            }
            if (s.commentaryReady) {
                item {
                    TextButton(onClick = { vm.openChapterCommentary() }) {
                        Text("\u00a7 Commentary on this chapter")
                    }
                }
            }
            items(s.verses, key = { it.verseKey }) { v ->
                val n = v.number.toIntOrNull() ?: -1
                VerseRow(
                    v = v,
                    translation = s.translationCode,
                    commentaryCount = s.commentaryCounts[n] ?: 0,
                    noteCount = s.noteCounts[n] ?: 0,
                    xrefCount = s.xrefCounts[n] ?: 0,
                    onWord = { vm.selectWord(it) },
                    onCommentary = { vm.openCommentary(v.verseKey) },
                    onNotes = { vm.openNotes(v.verseKey) },
                    onXrefs = { vm.openXrefs(v.verseKey) },
                )
            }
            item {
                ChapterStepper(
                    prev = vm.neighbour(-1),
                    next = vm.neighbour(1),
                    nameOf = { vm.bookName(it) },
                    onStep = { vm.step(it) },
                )
            }
        }
    }

    if (s.showDisplay) {
        ModalBottomSheet(onDismissRequest = { vm.closeDisplay() }) {
            DisplaySheet(
                fontSize = s.fontSize,
                palette = s.palette,
                onFontSize = { vm.setFontSize(it) },
                onPalette = { vm.setPalette(it) },
            )
        }
    }

    if (s.picking) {
        ModalBottomSheet(onDismissRequest = { vm.closePicker() }) {
            BookPicker(
                books = s.books,
                chaptersFor = s.pickingChaptersFor,
                onBook = { vm.pickBook(it) },
                onChapter = { b, n -> vm.open(b.code, n) },
            )
        }
    }

    s.timeline?.let { entries ->
        ModalBottomSheet(onDismissRequest = { vm.closeTimeline() }) {
            TimelineSheet(
                entries = entries,
                schemes = s.schemes,
                schemeId = s.schemeId,
                nameOf = { vm.bookName(it) },
                onScheme = { vm.chooseScheme(it) },
                onGo = { vm.goToFromTimeline(it) },
            )
        }
    }

    if (s.searching) {
        ModalBottomSheet(onDismissRequest = { vm.closeSearch() }) {
            SearchSheet(
                query = s.query,
                mode = s.searchMode,
                running = s.searchRunning,
                verses = s.hitsVerses,
                notes = s.hitsNotes,
                words = s.hitsWords,
                nameOf = { vm.bookName(it) },
                onQuery = { vm.setQuery(it) },
                onMode = { vm.setMode(it) },
                onGo = { vm.goToFromSearch(it) },
                onWord = { },
            )
        }
    }

    s.notes?.let { ns ->
        ModalBottomSheet(onDismissRequest = { vm.closeContext() }) {
            NotesSheet(s.sheetTitle, ns)
        }
    }

    s.xrefs?.let { xs ->
        ModalBottomSheet(onDismissRequest = { vm.closeContext() }) {
            XrefSheet(s.sheetTitle, xs, { vm.bookName(it) }) { vm.goTo(it) }
        }
    }

    if (s.showAbout) {
        ModalBottomSheet(onDismissRequest = { vm.closeAbout() }) {
            AboutSheet(s.translations, s.schemes, s.chronologyNotes)
        }
    }

    s.commentary?.let { units ->
        ModalBottomSheet(onDismissRequest = { vm.closeCommentary() }) {
            CommentarySheet(s.commentaryTitle, units)
        }
    }

    s.selected?.let { study ->
        ModalBottomSheet(onDismissRequest = { vm.clearSelection() }) {
            WordStudySheet(study, s.context, s.schemes, s.schemeId) { vm.chooseScheme(it) }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun TranslationPicker(
    current: String,
    options: List<TranslationInfo>,
    onPick: (String) -> Unit,
    onNeedOptions: () -> Unit,
) {
    var open by remember { mutableStateOf(false) }
    Box {
        TextButton(onClick = { onNeedOptions(); open = true }) {
            Text(current, style = MaterialTheme.typography.labelLarge)
        }
        DropdownMenu(expanded = open, onDismissRequest = { open = false }) {
            if (options.isEmpty()) {
                DropdownMenuItem(text = { Text("Loading\u2026") }, onClick = {})
            }
            options.forEach { t ->
                DropdownMenuItem(
                    text = { Text(t.name) },
                    onClick = { onPick(t.code); open = false },
                )
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun VerseRow(
    v: VerseBlock,
    translation: String,
    commentaryCount: Int,
    noteCount: Int,
    xrefCount: Int,
    onWord: (Token) -> Unit,
    onCommentary: () -> Unit,
    onNotes: () -> Unit,
    onXrefs: () -> Unit,
) {
    Row(Modifier.padding(vertical = 10.dp)) {
        Text(
            v.number,
            Modifier.width(32.dp),
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Column(Modifier.weight(1f)) {
            // Hebrew and Aramaic read right to left; Greek does not.
            CompositionLocalProvider(
                LocalLayoutDirection provides if (v.isRtl) LayoutDirection.Rtl else LayoutDirection.Ltr
            ) {
                FlowRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    v.tokens.forEach { t ->
                        Text(
                            t.surface,
                            Modifier.clickable { onWord(t) }.padding(vertical = 2.dp),
                            style = TextStyle(fontSize = if (t.isRtl) 21.sp else 18.sp),
                        )
                    }
                }
            }
            v.translations.firstOrNull { it.code == translation }?.let {
                Spacer(Modifier.height(4.dp))
                Text(
                    it.text,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            if (noteCount > 0 || xrefCount > 0 || commentaryCount > 0) {
                Spacer(Modifier.height(2.dp))
                FlowRow(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    if (noteCount > 0) {
                        TextButton(onClick = onNotes, contentPadding = PaddingValues(4.dp)) {
                            Text("\u270e $noteCount note" + if (noteCount == 1) "" else "s",
                                 style = MaterialTheme.typography.labelMedium)
                        }
                    }
                    if (xrefCount > 0) {
                        TextButton(onClick = onXrefs, contentPadding = PaddingValues(4.dp)) {
                            Text("\u21c4 $xrefCount link" + if (xrefCount == 1) "" else "s",
                                 style = MaterialTheme.typography.labelMedium)
                        }
                    }
                    if (commentaryCount > 0) {
                        TextButton(onClick = onCommentary, contentPadding = PaddingValues(4.dp)) {
                            Text(
                                "\u00a7 $commentaryCount commentar" +
                                    if (commentaryCount == 1) "y" else "ies",
                                style = MaterialTheme.typography.labelMedium,
                            )
                        }
                    }
                }
            }
        }
    }
    HorizontalDivider()
}
