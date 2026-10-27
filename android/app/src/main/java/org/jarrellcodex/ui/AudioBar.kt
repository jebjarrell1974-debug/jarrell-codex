package org.jarrellcodex.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.delay
import org.jarrellcodex.audio.Playback

/**
 * The bar across the bottom while something is being read.
 *
 * It says, in order: which chapter, what the recording actually covers, how
 * the starting point was arrived at, and who to thank. The second and third
 * of those exist because a reading that holds fourteen chapters and starts
 * at a guessed position would otherwise look like a reading of one chapter
 * that starts in the wrong place.
 */
@Composable
fun AudioBar(nameOf: (String) -> String, onStop: () -> Unit) {
    val s by Playback.state.collectAsState()
    if (!s.open) return

    // The player is the only thing that knows where it is, so ask it.
    LaunchedEffect(s.playing) {
        while (s.playing) {
            Playback.tick()
            delay(500)
        }
    }

    val r = s.reading ?: return
    Surface(
        Modifier.fillMaxWidth(),
        color = MaterialTheme.colorScheme.surface,
        tonalElevation = 3.dp,
        shadowElevation = 8.dp,
    ) {
        Column(Modifier.padding(start = 14.dp, end = 8.dp, top = 8.dp, bottom = 10.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text(label(s.chapterKey, nameOf),
                         style = MaterialTheme.typography.titleSmall,
                         fontWeight = FontWeight.SemiBold)
                    Text(
                        if (r.alone) "A reading of this chapter on its own"
                        else "One recording covers ${coverLabel(r.covers, nameOf)} " +
                             "— ${r.covers.size} chapters",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                IconButton(onClick = { Playback.skip(-30_000) },
                           enabled = s.durationMs > 0) {
                    Text("↶", style = MaterialTheme.typography.titleLarge)
                }
                FilledIconButton(
                    onClick = { Playback.toggle() },
                    enabled = !s.preparing,
                    modifier = Modifier.size(56.dp),
                ) {
                    Text(
                        when {
                            s.preparing -> "…"
                            s.playing -> "⏸"
                            else -> "▶"
                        },
                        style = MaterialTheme.typography.titleLarge,
                    )
                }
                IconButton(onClick = { Playback.skip(30_000) },
                           enabled = s.durationMs > 0) {
                    Text("↷", style = MaterialTheme.typography.titleLarge)
                }
                IconButton(onClick = onStop) {
                    Text("×", style = MaterialTheme.typography.titleLarge)
                }
            }

            if (s.durationMs > 0) {
                Slider(
                    value = s.positionMs.coerceIn(0, s.durationMs).toFloat(),
                    onValueChange = { Playback.seekTo(it.toInt()) },
                    valueRange = 0f..s.durationMs.toFloat(),
                )
                Row {
                    Text(clock(s.positionMs), style = MaterialTheme.typography.labelMedium,
                         color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Spacer(Modifier.weight(1f))
                    Text(clock(s.durationMs), style = MaterialTheme.typography.labelMedium,
                         color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }

            if (s.continued) {
                Text(
                    "The last reading finished, so this one carried on from it.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            s.error?.let {
                Text(it, style = MaterialTheme.typography.bodySmall,
                     color = MaterialTheme.colorScheme.error)
            }

            // Said every time, not once: a position worked out from verse
            // counts is not a timing anyone recorded, and a reader who thinks
            // it is will conclude the recording is wrong.
            if (s.estimated) {
                Text(
                    "Started at about ${clock(s.estimatedMs)}, an estimate for " +
                    "${label(s.chapterKey, nameOf)} worked out from verse counts " +
                    "rather than a timing anyone recorded. Drag the slider either " +
                    "way if it landed in the wrong place.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                TextButton(onClick = { Playback.restart() },
                           contentPadding = PaddingValues(vertical = 6.dp)) {
                    Text("Start at ${label(r.covers.first(), nameOf)} instead")
                }
            }

            Text(
                "Read by volunteers for LibriVox. Public domain. Streamed from " +
                "archive.org, not stored on this phone — the text is.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

private fun label(key: String, nameOf: (String) -> String): String {
    val p = key.split('.')
    return if (p.size >= 2) "${nameOf(p[0])} ${p[1]}" else key
}

private fun coverLabel(covers: List<String>, nameOf: (String) -> String): String {
    if (covers.isEmpty()) return ""
    val a = label(covers.first(), nameOf)
    val b = covers.last().substringAfterLast('.')
    return if (covers.size == 1) a else "$a–$b"
}

private fun clock(ms: Int): String {
    if (ms <= 0) return "0:00"
    val total = ms / 1000
    val h = total / 3600
    val m = (total % 3600) / 60
    val s = total % 60
    return if (h > 0) "%d:%02d:%02d".format(h, m, s) else "%d:%02d".format(m, s)
}
