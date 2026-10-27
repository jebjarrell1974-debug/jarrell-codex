package org.jarrellcodex.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import org.jarrellcodex.data.Plate

/**
 * All 150 of Dore's engravings, in the order he published them, each with
 * an honest account of itself.
 *
 * 125 sit at a verse. 20 illustrate Tobit, Judith, Baruch, the Greek
 * additions to Daniel and the Maccabees, which this Bible does not carry -
 * they are here rather than dropped, because a reader is entitled to see
 * what the set contains and to be told why those are not in the text. Five
 * carry no reference anywhere, and are listed as exactly that rather than
 * placed from however obvious the title looks.
 */
@Composable
fun GallerySheet(
    plates: List<Plate>,
    nameOf: (String) -> String,
    onGo: (String) -> Unit,
) {
    val placed = plates.count { it.placed }
    val outside = plates.count { !it.placed && it.outside.isNotEmpty() }
    val nowhere = plates.size - placed - outside

    LazyColumn(
        Modifier.fillMaxWidth(),
        contentPadding = PaddingValues(start = 20.dp, end = 20.dp, bottom = 40.dp),
    ) {
        item {
            Text("Doré's engravings", style = MaterialTheme.typography.titleLarge)
            Text("${plates.size} plates, engraved in 1866 · all public domain",
                 style = MaterialTheme.typography.labelMedium,
                 color = MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(Modifier.height(10.dp))
            Text(
                "Gustave Doré cut these for an illustrated Bible published in " +
                "1866. He died in 1883, so they have been free for anyone to use " +
                "for a century. They are one Victorian artist's reading of the " +
                "scene — not a photograph, and not evidence — but he was very " +
                "good, and where the printer said which passage a plate belongs " +
                "to, it sits there in the text.",
                style = MaterialTheme.typography.bodySmall,
            )
            Spacer(Modifier.height(8.dp))
            Text(
                "$placed are set at a verse. $outside illustrate books this Bible " +
                "does not carry, so they are here and not in the text. $nowhere " +
                "carry no reference at all; rather than guess a verse from the " +
                "title, they are listed as what they are.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(Modifier.height(6.dp))
        }
        items(plates, key = { it.id }) { pl ->
            HorizontalDivider(Modifier.padding(vertical = 14.dp))
            PlateFigure(pl)
            Text(
                "Plate ${pl.id}" +
                    if (pl.reference.isNotBlank())
                        " · printed as “${pl.reference}”" else "",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            when {
                pl.placed -> {
                    val p = pl.at.split('.')
                    val label = if (p.size >= 2) "${nameOf(p[0])} ${p[1]}" else pl.at
                    TextButton(onClick = { onGo(pl.at) },
                               contentPadding = PaddingValues(vertical = 6.dp)) {
                        Text("Read $label →")
                    }
                }
                pl.outside.isNotEmpty() -> Text(
                    "Illustrates ${pl.outside}.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                else -> Text(
                    "No passage is recorded for this plate, so it is not set " +
                    "in the text.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}
