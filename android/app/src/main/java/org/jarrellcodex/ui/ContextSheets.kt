package org.jarrellcodex.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import org.jarrellcodex.data.CrossRef
import org.jarrellcodex.data.TranslationNote

/**
 * The translators' notes on a verse: what the original says, where the idiom
 * will not carry, what a first reader would have heard. Written for people
 * doing the work of translating, which makes them unusually plain.
 */
@Composable
fun NotesSheet(title: String, notes: List<TranslationNote>) {
    Column(
        Modifier.fillMaxWidth().verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp).padding(bottom = 32.dp),
    ) {
        Text(title, style = MaterialTheme.typography.labelSmall,
             color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(10.dp))
        if (notes.isEmpty()) {
            Text("No notes on this verse.", style = MaterialTheme.typography.bodyMedium)
            return@Column
        }
        notes.forEach { n ->
            HorizontalDivider(Modifier.padding(vertical = 14.dp))
            n.quote?.takeIf { it.isNotBlank() }?.let {
                Text(it, fontSize = 17.sp, color = MaterialTheme.colorScheme.primary)
                Spacer(Modifier.height(6.dp))
            }
            // The source marks emphasis with **stars**; strip them rather than
            // printing the punctuation at the reader.
            Text(n.body.replace("**", ""), style = MaterialTheme.typography.bodyMedium,
                 lineHeight = 21.sp)
            n.category?.takeIf { it.isNotBlank() }?.let {
                Spacer(Modifier.height(5.dp))
                Text(it, style = MaterialTheme.typography.labelSmall,
                     color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        Spacer(Modifier.height(18.dp))
        Text(notes.first().source, style = MaterialTheme.typography.labelSmall,
             color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

/** Where else the same thread runs. The bar is relative weight, not proof. */
@Composable
fun XrefSheet(
    title: String,
    xrefs: List<CrossRef>,
    nameOf: (String) -> String,
    onGo: (String) -> Unit,
) {
    val top = xrefs.firstOrNull()?.votes ?: 1
    Column(
        Modifier.fillMaxWidth().verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp).padding(bottom = 32.dp),
    ) {
        Text(title, style = MaterialTheme.typography.labelSmall,
             color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(8.dp))
        Text(
            "Ranked by how strongly these passages have been linked. The bar " +
                "is relative weight, not certainty.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Spacer(Modifier.height(10.dp))
        xrefs.forEach { x ->
            val frac = (x.votes.toFloat() / (if (top > 0) top else 1)).coerceIn(0.06f, 1f)
            TextButton(
                onClick = { onGo(x.toKey) },
                modifier = Modifier.fillMaxWidth(),
                contentPadding = PaddingValues(vertical = 10.dp),
            ) {
                Column(Modifier.fillMaxWidth()) {
                    Text(x.label(nameOf(x.book)),
                         style = MaterialTheme.typography.bodyMedium)
                    Spacer(Modifier.height(5.dp))
                    Box(
                        Modifier.fillMaxWidth(frac).height(3.dp)
                            .clip(RoundedCornerShape(2.dp))
                            .background(MaterialTheme.colorScheme.primary.copy(alpha = .55f)),
                    )
                }
            }
        }
        Spacer(Modifier.height(16.dp))
        Text("Treasury of Scripture Knowledge and related sets, via OpenBible.info",
             style = MaterialTheme.typography.labelSmall,
             color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}
