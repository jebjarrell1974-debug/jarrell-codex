package org.jarrellcodex.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/**
 * Text size and colour, the way the website offers them.
 *
 * Two deliberate choices, both from the research on reading at seventy and
 * both the opposite of a designer's instinct:
 *
 * No dropdowns. Sayago and Blat found a select control defeated every older
 * participant they tested, while larger tappable rows did not. So every
 * choice here is a button big enough to hit.
 *
 * A live sample at the chosen size. Someone deciding whether 24sp is enough
 * should not have to close the sheet, look, and come back.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DisplaySheet(
    fontSize: Int,
    palette: Palette,
    onFontSize: (Int) -> Unit,
    onPalette: (Palette) -> Unit,
) {
    Column(
        Modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState())
            .padding(start = 20.dp, end = 20.dp, bottom = 32.dp),
    ) {
        Text("Reading", style = MaterialTheme.typography.titleLarge)

        Spacer(Modifier.height(18.dp))
        Text("Text size", style = MaterialTheme.typography.labelLarge,
             color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(8.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            SizeButton("A−", "Smaller text",
                enabled = fontSize > FS_MIN) { onFontSize(fontSize - 1) }
            Column(
                Modifier.weight(1f).padding(horizontal = 12.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Text("${fontSize}pt", style = MaterialTheme.typography.titleMedium,
                     fontWeight = FontWeight.SemiBold)
                Text(
                    when {
                        fontSize <= 18 -> "smaller than the default"
                        fontSize == FS_DEFAULT -> "the default"
                        else -> "larger than the default"
                    },
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center,
                )
            }
            SizeButton("A+", "Larger text",
                enabled = fontSize < FS_MAX) { onFontSize(fontSize + 1) }
        }

        Spacer(Modifier.height(14.dp))
        // The sample is rendered at the size being chosen, not at the size
        // the app is currently using, so the choice can be judged before it
        // is made rather than after.
        Surface(
            Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp),
            color = MaterialTheme.colorScheme.surface,
            border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
        ) {
            Text(
                "In the beginning God created the heaven and the earth.",
                Modifier.padding(14.dp),
                fontSize = (fontSize * 17f / 16f).sp,
                lineHeight = (fontSize * 29f / 16f).sp,
                color = MaterialTheme.colorScheme.onSurface,
            )
        }

        Spacer(Modifier.height(24.dp))
        Text("Colours", style = MaterialTheme.typography.labelLarge,
             color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(4.dp))
        Text(
            "Every one of these was checked so the text stands at least seven " +
            "times clearer than its background — half again the usual " +
            "standard, which is itself set from what a typical eighty-year-old " +
            "eye can tell apart.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Spacer(Modifier.height(10.dp))
        Palette.entries.forEach { sc ->
            PaletteRow(sc, sc == palette) { onPalette(sc) }
            Spacer(Modifier.height(8.dp))
        }
    }
}

@Composable
private fun SizeButton(
    label: String,
    describe: String,
    enabled: Boolean,
    onClick: () -> Unit,
) {
    OutlinedButton(
        onClick = onClick,
        enabled = enabled,
        modifier = Modifier
            .widthIn(min = 80.dp)
            .heightIn(min = 60.dp)
            .semantics { contentDescription = describe },
    ) {
        Text(label, style = MaterialTheme.typography.titleMedium,
             fontWeight = FontWeight.SemiBold)
    }
}

/**
 * The swatch is painted in the scheme's own colours rather than the one in
 * use, so the choice shows what it will look like.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun PaletteRow(sc: Palette, selected: Boolean, onClick: () -> Unit) {
    val paper = Color(sc.paper or 0xFF000000)
    val ink = Color(sc.ink or 0xFF000000)
    val soft = Color(sc.soft or 0xFF000000)
    Surface(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth().heightIn(min = 72.dp),
        shape = RoundedCornerShape(12.dp),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(
            if (selected) 2.dp else 1.dp,
            if (selected) MaterialTheme.colorScheme.primary
            else MaterialTheme.colorScheme.outline,
        ),
    ) {
        Row(
            Modifier.padding(12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                Modifier
                    .size(52.dp)
                    .background(paper, RoundedCornerShape(9.dp))
                    .border(1.dp, soft, RoundedCornerShape(9.dp)),
                contentAlignment = Alignment.Center,
            ) {
                Text("Aa", color = ink,
                     style = MaterialTheme.typography.titleMedium,
                     fontWeight = FontWeight.SemiBold)
            }
            Spacer(Modifier.width(14.dp))
            Column(Modifier.weight(1f)) {
                Text(
                    (if (selected) "✓ " else "") + sc.label,
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Normal,
                )
                Text(sc.note, style = MaterialTheme.typography.bodySmall,
                     color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}
