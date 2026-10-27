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
import androidx.compose.ui.CompositionLocalProvider
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
        TopAppBar(title = { Text("${s.book} ${s.chapter}") })
    }) { pad ->
        LazyColumn(
            Modifier.fillMaxSize().padding(pad),
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
        ) {
            items(s.verses, key = { it.verseKey }) { v -> VerseRow(v) { vm.selectWord(it) } }
        }
    }

    s.selected?.let { study ->
        ModalBottomSheet(onDismissRequest = { vm.clearSelection() }) {
            WordStudySheet(study, s.context, s.schemes, s.schemeId) { vm.chooseScheme(it) }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun VerseRow(v: VerseBlock, onWord: (Token) -> Unit) {
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
            v.translations.firstOrNull { it.code == "KJV" }?.let {
                Spacer(Modifier.height(4.dp))
                Text(
                    it.text,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
    HorizontalDivider()
}
