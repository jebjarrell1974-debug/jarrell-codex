package org.jarrellcodex.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.clickable
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import org.jarrellcodex.data.*

@Composable
fun WordStudySheet(
    study: WordStudy,
    context: VerseContext?,
    schemes: List<Scheme>,
    schemeId: String,
    photoOf: (String) -> Photo? = { null },
    onScheme: (String) -> Unit,
) {
    Column(
        Modifier.fillMaxWidth().verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp).padding(bottom = 32.dp),
    ) {
        Text(
            study.token.verseKey.replace('.', ' ') + " · word ${study.token.position}",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Spacer(Modifier.height(6.dp))
        Row(verticalAlignment = Alignment.Bottom) {
            Text(study.token.surface, fontSize = if (study.token.isRtl) 30.sp else 26.sp)
            study.token.translit?.let {
                Spacer(Modifier.width(10.dp))
                Text(it, fontStyle = FontStyle.Italic,
                     color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        study.token.gloss?.let { Text(it, style = MaterialTheme.typography.bodyLarge) }

        // One printed word can hold a prefix, a root and a suffix, each with its
        // own Strong's number and its own grammar. Showing only the whole word
        // would make the concordance lie.
        study.morphemes.forEach { m ->
            HorizontalDivider(Modifier.padding(vertical = 14.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                m.surface?.takeIf { it.isNotBlank() }?.let {
                    Text(it, fontSize = if (study.token.isRtl) 22.sp else 19.sp)
                    Spacer(Modifier.width(10.dp))
                }
                m.strongs?.let { AssistChip(onClick = {}, label = { Text(it) }) }
            }
            m.lemma?.let {
                Spacer(Modifier.height(6.dp))
                Text(it + (m.gloss?.let { g -> " — $g" } ?: ""),
                     style = MaterialTheme.typography.bodyLarge)
            }
            m.parsing?.let {
                Spacer(Modifier.height(4.dp))
                Text(it, style = MaterialTheme.typography.bodySmall,
                     color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            m.definition?.let {
                Spacer(Modifier.height(6.dp))
                Text(it, style = MaterialTheme.typography.bodySmall)
            }
            m.strongsSimple?.let { simple ->
                study.counts[simple]?.let { n ->
                    Spacer(Modifier.height(6.dp))
                    Text("$n occurrence${if (n == 1) "" else "s"} of $simple",
                         style = MaterialTheme.typography.labelSmall,
                         color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }

        context?.let { ctx ->
            if (ctx.places.isNotEmpty() || ctx.people.isNotEmpty()) {
                HorizontalDivider(Modifier.padding(vertical = 14.dp))
                ctx.places.forEach { p ->
                    // A place nobody can locate gets no pin and says so. The app
                    // never invents coordinates to fill a gap.
                    val where = when {
                        p.hasPin -> "%.4f, %.4f".format(p.latitude, p.longitude)
                        p.status == "region" -> "region"
                        else -> "location unknown"
                    }
                    Text("${p.name} · $where", style = MaterialTheme.typography.bodySmall)
                    // Somewhere that is still there, photographed. Not every
                    // place has one, and a place with no photograph simply
                    // has none - nothing stands in for it.
                    photoOf(p.name)?.let { PhotoFigure(it) }
                }
                ctx.people.forEach { p ->
                    val dates = listOfNotNull(formatYear(p.birthYear), formatYear(p.deathYear))
                    Text(p.name + if (dates.isNotEmpty()) " · ${dates.joinToString(" – ")}" else "",
                         style = MaterialTheme.typography.bodySmall)
                }
            }

            if (ctx.events.isNotEmpty()) {
                HorizontalDivider(Modifier.padding(vertical = 14.dp))
                Text("Dating", style = MaterialTheme.typography.labelSmall,
                     color = MaterialTheme.colorScheme.onSurfaceVariant)
                Spacer(Modifier.height(8.dp))
                SchemePicker(schemes, schemeId, onScheme)
                Spacer(Modifier.height(10.dp))
                ctx.events.forEach { e ->
                    Row(Modifier.fillMaxWidth().padding(vertical = 3.dp),
                        horizontalArrangement = Arrangement.SpaceBetween) {
                        Text(e.title, Modifier.weight(1f),
                             style = MaterialTheme.typography.bodySmall)
                        Spacer(Modifier.width(12.dp))
                        val shown = formatYear(e.startYear)
                        Text(
                            shown ?: "no date in this scheme",
                            style = MaterialTheme.typography.bodySmall,
                            fontStyle = if (shown == null) FontStyle.Italic else FontStyle.Normal,
                            color = if (shown == null) MaterialTheme.colorScheme.onSurfaceVariant
                                    else MaterialTheme.colorScheme.onSurface,
                        )
                    }
                }
                schemes.firstOrNull { it.schemeId == schemeId }?.let { meta ->
                    Spacer(Modifier.height(10.dp))
                    Text(meta.summary, style = MaterialTheme.typography.bodySmall,
                         color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Spacer(Modifier.height(4.dp))
                    Text("Source: ${meta.source}", style = MaterialTheme.typography.labelSmall,
                         color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun SchemePicker(schemes: List<Scheme>, current: String, onPick: (String) -> Unit) {
    var open by remember { mutableStateOf(false) }
    val label = schemes.firstOrNull { it.schemeId == current }?.name ?: current
    Box {
        AssistChip(onClick = { open = true }, label = { Text(label) })
        DropdownMenu(expanded = open, onDismissRequest = { open = false }) {
            schemes.forEach { s ->
                DropdownMenuItem(
                    text = {
                        Text(s.name + if (s.coverage == "none") "  (no dates loaded)" else "")
                    },
                    onClick = { onPick(s.schemeId); open = false },
                )
            }
        }
    }
}
