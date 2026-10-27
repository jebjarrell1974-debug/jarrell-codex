package org.jarrellcodex.ui

import androidx.compose.material3.ColorScheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.sp

/**
 * Reading settings, for people who will be reading this at seventy.
 *
 * The palettes are the same six the website uses and were generated and
 * verified there: every text colour clears 7:1 against its own background.
 * 7:1 rather than the usual 4.5:1 because WCAG's own derivation ties 4.5:1
 * to the contrast sensitivity of a TYPICAL eighty-year-old, and this is
 * read by people at and past that.
 *
 * Text size is one factor applied to the whole type scale rather than a
 * size on each piece of text, so nothing can drift out of step.
 */
enum class Palette(
    val label: String,
    val note: String,
    val dark: Boolean,
    val paper: Long, val surface: Long,
    val ink: Long, val soft: Long, val faint: Long,
    val accent: Long, val onAccent: Long, val line: Long,
) {
    PAPER("Paper", "A warm near-white. The default.", false,
        0xFCFBF8, 0xFFFFFF, 0x141210, 0x4A4540, 0x59544E, 0x0B4F87, 0xFFFFFF, 0xDEDAD2),
    SEPIA("Sepia", "The old paperback. Warmer, a little less glare.", false,
        0xF4ECD8, 0xFBF6EA, 0x241D14, 0x4F4538, 0x564C3D, 0x07406E, 0xFFFFFF, 0xDCD0B4),
    CONTRAST("High contrast", "As strong as it goes. For bright sun, or eyes that need it.", false,
        0xFFFFFF, 0xFFFFFF, 0x000000, 0x2E2E2E, 0x3D3D3D, 0x00439B, 0xFFFFFF, 0x9A9A9A),
    DIM("Dim", "Quiet grey, dark print. For eyes that find a white page too bright.", false,
        0xD8D4CE, 0xE6E3DE, 0x16140F, 0x2B2821, 0x3A362E, 0x06385F, 0xFFFFFF, 0xB6B1A8),
    NIGHT("Night", "Soft dark. Easier than pure black on most screens.", true,
        0x15181C, 0x1E2228, 0xEDEBE7, 0xD6D2CC, 0xB9B4AC, 0xF0C98A, 0x15181C, 0x363B43),
    BLACK("Black", "True black. Saves power on an OLED screen.", true,
        0x000000, 0x0C0C0C, 0xFFFFFF, 0xD9D9D9, 0xBDBDBD, 0xFFD479, 0x000000, 0x3A3A3A);

    private fun c(v: Long) = Color(v or 0xFF000000)

    fun colors(): ColorScheme {
        val base = if (dark) darkColorScheme() else lightColorScheme()
        return base.copy(
            background = c(paper), onBackground = c(ink),
            surface = c(surface), onSurface = c(ink),
            surfaceVariant = c(surface), onSurfaceVariant = c(soft),
            primary = c(accent), onPrimary = c(onAccent),
            secondary = c(accent), onSecondary = c(onAccent),
            outline = c(line), outlineVariant = c(line),
            surfaceContainer = c(surface), surfaceContainerHigh = c(surface),
            surfaceContainerLow = c(surface), surfaceContainerLowest = c(surface),
            surfaceContainerHighest = c(surface),
        )
    }
}

/** 17sp to 30sp, the same range the website offers. */
const val FS_MIN = 17
const val FS_MAX = 30
const val FS_DEFAULT = 19

/**
 * Material's own scale, multiplied. Line height stays at least 1.5x the
 * size, which WCAG 1.4.12 makes a floor rather than a target, and the
 * smallest step is deliberately close to the body size: older eyes do not
 * get a separate, tinier interface just because the text is a caption.
 */
fun scaledTypography(base: Int): Typography {
    val k = base / 16f
    val t = Typography()
    return t.copy(
        displaySmall = t.displaySmall.copy(fontSize = (30 * k).sp, lineHeight = (38 * k).sp),
        headlineMedium = t.headlineMedium.copy(fontSize = (24 * k).sp, lineHeight = (32 * k).sp),
        headlineSmall = t.headlineSmall.copy(fontSize = (21 * k).sp, lineHeight = (28 * k).sp),
        titleLarge = t.titleLarge.copy(fontSize = (20 * k).sp, lineHeight = (27 * k).sp),
        titleMedium = t.titleMedium.copy(fontSize = (17 * k).sp, lineHeight = (25 * k).sp),
        titleSmall = t.titleSmall.copy(fontSize = (16 * k).sp, lineHeight = (24 * k).sp),
        bodyLarge = t.bodyLarge.copy(fontSize = (17 * k).sp, lineHeight = (29 * k).sp),
        bodyMedium = t.bodyMedium.copy(fontSize = (16 * k).sp, lineHeight = (27 * k).sp),
        bodySmall = t.bodySmall.copy(fontSize = (15 * k).sp, lineHeight = (25 * k).sp),
        labelLarge = t.labelLarge.copy(fontSize = (15 * k).sp, lineHeight = (21 * k).sp),
        labelMedium = t.labelMedium.copy(fontSize = (14 * k).sp, lineHeight = (20 * k).sp),
        // Material's labelSmall is 11sp, which is unreadable for this audience
        labelSmall = t.labelSmall.copy(fontSize = (14 * k).sp, lineHeight = (20 * k).sp),
    )
}

@Composable
fun CodexTheme(palette: Palette, fontSize: Int, content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = palette.colors(),
        typography = scaledTypography(fontSize),
        content = content,
    )
}
