package org.jarrellcodex.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.horizontalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import org.jarrellcodex.data.CommentaryUnit

/**
 * The commentators on one verse, or on a chapter as a whole.
 *
 * They are shown with their dates attached and with what each one was
 * actually writing about. Henry writes on John 3:1-21 as a block; the Geneva
 * note is on verse 16 alone. Presenting both as "commentary on verse 16"
 * would misrepresent what the man wrote.
 */
@Composable
fun CommentarySheet(
    title: String,
    units: List<CommentaryUnit>,
) {
    var filter by remember(title) { mutableStateOf<String?>(null) }
    val present = remember(units) { units.map { it.sourceId to it.author }.distinct() }
    val shown = remember(units, filter) {
        filter?.let { f -> units.filter { it.sourceId == f } } ?: units
    }

    Column(
        Modifier.fillMaxWidth().verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp).padding(bottom = 32.dp),
    ) {
        Text(
            title,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Spacer(Modifier.height(8.dp))

        if (units.isEmpty()) {
            Text(
                "None of the six wrote anything here.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            return@Column
        }

        Text(
            "Six commentators, writing between 1599 and 1885. They disagree " +
                "with each other, and with you. That is what they are for.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )

        if (present.size > 1) {
            Spacer(Modifier.height(12.dp))
            Row(
                Modifier.horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                FilterChip(
                    selected = filter == null,
                    onClick = { filter = null },
                    label = { Text("All ${units.size}") },
                )
                present.forEach { (id, author) ->
                    val n = units.count { it.sourceId == id }
                    FilterChip(
                        selected = filter == id,
                        onClick = { filter = if (filter == id) null else id },
                        label = { Text("$author $n") },
                    )
                }
            }
        }

        shown.forEach { u ->
            HorizontalDivider(Modifier.padding(vertical = 16.dp))
            Text(u.author, fontWeight = FontWeight.SemiBold,
                 style = MaterialTheme.typography.titleSmall)
            Text(
                "${u.work} · ${u.coverage}",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            u.title?.let {
                Spacer(Modifier.height(8.dp))
                Text(it, fontStyle = FontStyle.Italic,
                     style = MaterialTheme.typography.bodyMedium)
            }
            u.paragraphs.forEach { p ->
                Spacer(Modifier.height(10.dp))
                Text(p, style = MaterialTheme.typography.bodyMedium, lineHeight = 22.sp)
            }
        }

        Spacer(Modifier.height(20.dp))
        Text(
            "All six are in the public domain. Nothing under copyright was included.",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

/**
 * Offered when the commentary has not been unpacked. The asset is already in
 * the app, so this costs disk, not data - which matters on a phone that has
 * never had a signal.
 */
@Composable
fun AddCommentaryCard(
    unpacking: Boolean,
    progress: Float,
    failure: String? = null,
    onAdd: () -> Unit,
) {
    Card(Modifier.fillMaxWidth().padding(vertical = 12.dp)) {
        Column(Modifier.padding(18.dp)) {
            Text("Add the commentators", fontWeight = FontWeight.SemiBold,
                 style = MaterialTheme.typography.titleSmall)
            Spacer(Modifier.height(8.dp))
            Text(
                "Matthew Henry, the 1599 Geneva notes, Calvin, Poole, Trapp and " +
                    "Spurgeon — 91,008 pieces of commentary covering almost " +
                    "every verse. They are already inside the app, so this needs " +
                    "no connection. It needs about 148 MB of space, and you can " +
                    "give it back later.",
                style = MaterialTheme.typography.bodySmall,
            )
            Spacer(Modifier.height(14.dp))
            if (unpacking) {
                LinearProgressIndicator(
                    progress = { progress },
                    modifier = Modifier.fillMaxWidth(),
                )
                Spacer(Modifier.height(8.dp))
                Text(
                    "Unpacking — ${(progress * 100).toInt()}%",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            } else {
                failure?.let {
                    Text(
                        it,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.error,
                    )
                    Spacer(Modifier.height(12.dp))
                }
                Button(onClick = onAdd) {
                    Text(if (failure == null) "Add them" else "Try again")
                }
            }
        }
    }
}
