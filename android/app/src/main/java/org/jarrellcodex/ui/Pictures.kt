package org.jarrellcodex.ui

import android.content.Intent
import android.graphics.Bitmap
import android.net.Uri
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import org.jarrellcodex.data.Photo
import org.jarrellcodex.data.Pictures
import org.jarrellcodex.data.Plate

/**
 * A picture out of the app's own assets, decoded at the width it will be
 * drawn at and never larger.
 *
 * Reserves the right space before the bitmap arrives, from the dimensions
 * the manifest already carries, so a chapter does not jump about under the
 * reader's thumb as engravings decode.
 */
@Composable
private fun AssetImage(
    asset: String,
    width: Int,
    height: Int,
    describe: String,
    modifier: Modifier = Modifier,
) {
    val ctx = LocalContext.current
    val cfg = LocalConfiguration.current
    val px = with(LocalDensity.current) { (cfg.screenWidthDp.dp - 32.dp).roundToPx() }
    var bmp by remember(asset, px) { mutableStateOf<Bitmap?>(null) }
    LaunchedEffect(asset, px) { bmp = Pictures.bitmap(ctx, asset, px) }

    val ratio = if (width > 0 && height > 0) width.toFloat() / height else 3f / 4f
    val box = modifier
        .fillMaxWidth()
        .aspectRatio(ratio)
        .clip(RoundedCornerShape(8.dp))
    val b = bmp
    if (b == null) {
        Box(box.background(MaterialTheme.colorScheme.surfaceVariant))
    } else {
        Image(
            bitmap = b.asImageBitmap(),
            contentDescription = describe,
            modifier = box,
            contentScale = ContentScale.FillWidth,
        )
    }
}

/**
 * One of Dore's engravings, set at the verse it illustrates.
 *
 * Dore died in 1883, so these have been in the public domain for a century.
 * The reference under each one is the printer's own, not this app's reading
 * of it, which is why it is shown as printed.
 */
@Composable
fun PlateFigure(plate: Plate) {
    val ctx = LocalContext.current
    Column(Modifier.padding(vertical = 16.dp)) {
        AssetImage(
            asset = plate.asset,
            width = plate.width, height = plate.height,
            describe = "${plate.title}, engraved by Gustave Doré",
        )
        Spacer(Modifier.height(8.dp))
        Text(plate.title, style = MaterialTheme.typography.bodyMedium,
             fontWeight = FontWeight.SemiBold)
        if (plate.reference.isNotBlank()) {
            Text(plate.reference, style = MaterialTheme.typography.labelMedium,
                 color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("Gustave Doré, 1866. Public domain.",
                 style = MaterialTheme.typography.labelMedium,
                 color = MaterialTheme.colorScheme.onSurfaceVariant)
            if (plate.page.isNotBlank()) {
                TextButton(onClick = { open(ctx, plate.page) },
                           contentPadding = PaddingValues(horizontal = 8.dp)) {
                    Text("Source", style = MaterialTheme.typography.labelMedium)
                }
            }
        }
    }
}

/**
 * A photograph of a place that is still there.
 *
 * The credit line is the licence's requirement and the reader's only way to
 * check, so it names the photographer and links both the licence and the
 * page the file came from.
 */
@Composable
fun PhotoFigure(photo: Photo) {
    val ctx = LocalContext.current
    Column(Modifier.padding(vertical = 12.dp)) {
        AssetImage(
            asset = photo.asset,
            width = photo.width, height = photo.height,
            describe = "A photograph of ${photo.name}",
        )
        Spacer(Modifier.height(6.dp))
        Text(
            buildString {
                append(photo.name)
                if (photo.artist.isNotBlank()) append(" · ").append(photo.artist)
                if (photo.licence.isNotBlank()) append(" · ").append(photo.licence)
            },
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Row {
            if (photo.page.isNotBlank()) {
                TextButton(onClick = { open(ctx, photo.page) },
                           contentPadding = PaddingValues(horizontal = 8.dp)) {
                    Text("Where it came from", style = MaterialTheme.typography.labelMedium)
                }
            }
            if (photo.licenceUrl.isNotBlank()) {
                TextButton(onClick = { open(ctx, photo.licenceUrl) },
                           contentPadding = PaddingValues(horizontal = 8.dp)) {
                    Text("Licence", style = MaterialTheme.typography.labelMedium)
                }
            }
        }
    }
}

private fun open(ctx: android.content.Context, url: String) {
    runCatching {
        ctx.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url))
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
    }
}
