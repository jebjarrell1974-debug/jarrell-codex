package org.jarrellcodex.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import org.jarrellcodex.data.Scheme
import org.jarrellcodex.data.TimelineEntry

/**
 * The story in date order, under whichever chronology the reader picks.
 *
 * The schemes disagree, and that disagreement is shown rather than hidden.
 * A scheme that fixes only a handful of dates says so at the top, and its
 * undated events sit below in the order the text tells them, labelled as
 * undated. No scheme ever borrows another's year.
 */
@Composable
fun TimelineSheet(
    entries: List<TimelineEntry>,
    schemes: List<Scheme>,
    schemeId: String,
    nameOf: (String) -> String,
    onScheme: (String) -> Unit,
    onGo: (String) -> Unit,
) {
    val dated = entries.count { it.dated }
    val meta = schemes.firstOrNull { it.schemeId == schemeId }

    LazyColumn(
        Modifier.fillMaxWidth().heightIn(max = 620.dp)
            .padding(horizontal = 20.dp),
        contentPadding = PaddingValues(bottom = 28.dp),
    ) {
        item {
            Text("The story in order", fontWeight = FontWeight.SemiBold,
                 style = MaterialTheme.typography.titleMedium)
            Text(
                "$dated of ${entries.size} events dated in this scheme",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(Modifier.height(10.dp))
            SchemePicker(schemes, schemeId, onScheme)
            meta?.let {
                Spacer(Modifier.height(10.dp))
                Text(it.summary, style = MaterialTheme.typography.bodySmall,
                     lineHeight = 19.sp)
                if (it.source.isNotBlank()) {
                    Text(it.source, style = MaterialTheme.typography.labelSmall,
                         color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
            if (dated in 1 until 50) {
                Spacer(Modifier.height(12.dp))
                Card {
                    Text(
                        "This scheme anchors only $dated event" +
                            (if (dated == 1) "" else "s") + ". Its published work " +
                            "fixes a handful of dates and leaves the rest to be " +
                            "worked out from them, so there is no full ordering " +
                            "to show. The events below the dated ones are in the " +
                            "order the text tells them, not in a date order this " +
                            "scheme would vouch for.",
                        Modifier.padding(14.dp),
                        style = MaterialTheme.typography.bodySmall, lineHeight = 19.sp,
                    )
                }
            } else if (dated == 0) {
                Spacer(Modifier.height(12.dp))
                Card {
                    Text(
                        "No dates are loaded for this scheme, so the events below " +
                            "are in the order the text tells them. Pick Floyd Nolen " +
                            "Jones for a dated sequence.",
                        Modifier.padding(14.dp),
                        style = MaterialTheme.typography.bodySmall, lineHeight = 19.sp,
                    )
                }
            }
            Spacer(Modifier.height(8.dp))
            HorizontalDivider()
        }

        items(entries, key = { it.eventId }) { e ->
            TextButton(
                onClick = { e.firstRef?.let(onGo) },
                enabled = e.firstRef != null,
                modifier = Modifier.fillMaxWidth(),
                contentPadding = PaddingValues(vertical = 10.dp),
            ) {
                Column(Modifier.fillMaxWidth()) {
                    Text(
                        e.whenText,
                        style = MaterialTheme.typography.labelMedium,
                        fontStyle = if (e.dated) FontStyle.Normal else FontStyle.Italic,
                        color = if (e.dated) MaterialTheme.colorScheme.primary
                                else MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Spacer(Modifier.height(2.dp))
                    Text(e.title, style = MaterialTheme.typography.bodyMedium)
                    e.firstRef?.let { ref ->
                        val p = ref.split('.')
                        if (p.size >= 3) {
                            Text(
                                "${nameOf(p[0])} ${p[1]}:${p[2]}" +
                                    if (e.verseCount > 1) "  ·  ${e.verseCount} verses" else "",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }
                }
            }
            HorizontalDivider()
        }
    }
}
