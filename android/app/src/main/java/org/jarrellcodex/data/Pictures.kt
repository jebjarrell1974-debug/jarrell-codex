package org.jarrellcodex.data

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.util.LruCache
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject

/**
 * The photographs of the places and Dore's engravings, read straight out of
 * the app's assets.
 *
 * Both sets ship inside the app rather than being downloaded, and are
 * decoded from the asset stream rather than copied to disk first: 60 MB of
 * already-compressed WebP would only be 60 MB again in app storage, and the
 * app's whole promise is that it works the moment it is installed.
 *
 * Every picture carries its own licence, its photographer or engraver, and
 * a link to where it came from. None of that is optional: a free Bible that
 * strips attribution off other people's work is not free, it is just taking.
 */

data class Photo(
    val name: String,
    val file: String,
    val width: Int,
    val height: Int,
    val licence: String,
    val licenceUrl: String,
    val artist: String,
    val page: String,
) {
    val asset: String get() = "pix/$file"
}

data class Plate(
    val id: String,
    val file: String,
    val title: String,
    val width: Int,
    val height: Int,
    /** The printer's own reference, e.g. "Gen. 1:1-5". May be blank. */
    val reference: String,
    val page: String,
) {
    val asset: String get() = "dore/$file"
}

class Pictures private constructor(
    private val photos: Map<String, Photo>,
    private val plates: Map<String, Plate>,
    private val atVerse: Map<String, List<String>>,
) {
    val photoCount: Int get() = photos.size
    val plateCount: Int get() = plates.size

    /** The place names in the database are the keys of the photo manifest. */
    fun photo(placeName: String): Photo? = photos[placeName]

    /** Engravings that belong at this verse, in plate order. */
    fun platesAt(verseKey: String): List<Plate> =
        (atVerse[verseKey] ?: emptyList()).mapNotNull { plates[it] }

    companion object {
        @Volatile private var cached: Pictures? = null

        suspend fun load(context: Context): Pictures? = withContext(Dispatchers.IO) {
            cached ?: runCatching {
                val a = context.assets

                val pm = JSONObject(
                    a.open("pix_manifest.json").use { it.readBytes() }
                        .toString(Charsets.UTF_8))
                val photos = HashMap<String, Photo>(pm.length() * 2)
                for (name in pm.keys()) {
                    val o = pm.getJSONObject(name)
                    photos[name] = Photo(
                        name = name,
                        file = o.getString("file"),
                        width = o.optInt("w"), height = o.optInt("h"),
                        licence = o.optString("licence", ""),
                        licenceUrl = o.optString("licurl", ""),
                        artist = o.optString("artist", ""),
                        page = o.optString("page", ""),
                    )
                }

                val dj = JSONObject(
                    a.open("dore.json").use { it.readBytes() }
                        .toString(Charsets.UTF_8))
                val po = dj.getJSONObject("plates")
                val plates = HashMap<String, Plate>(po.length() * 2)
                for (id in po.keys()) {
                    val o = po.getJSONObject(id)
                    plates[id] = Plate(
                        id = id,
                        file = o.getString("file"),
                        title = o.optString("title", ""),
                        width = o.optInt("w"), height = o.optInt("h"),
                        reference = o.optString("ref", ""),
                        page = o.optString("page", ""),
                    )
                }

                val ao = dj.getJSONObject("at")
                val at = HashMap<String, List<String>>(ao.length() * 2)
                for (key in ao.keys()) {
                    val arr = ao.getJSONArray(key)
                    val ids = ArrayList<String>(arr.length())
                    for (i in 0 until arr.length()) ids.add(arr.getString(i))
                    at[key] = ids
                }

                Pictures(photos, plates, at)
            }.getOrNull()?.also { cached = it }
        }

        /**
         * Decoded at roughly the width it will be drawn at.
         *
         * A 900x1219 engraving is 4.4 MB as ARGB_8888, and a chapter can
         * carry several. Halving twice brings that under 300 KB with no
         * visible loss on a phone, and the cache is sized in kilobytes so
         * it cannot grow into the reason the app is killed.
         */
        private val bitmaps = object : LruCache<String, Bitmap>(24 * 1024) {
            override fun sizeOf(key: String, value: Bitmap) = value.byteCount / 1024
        }

        suspend fun bitmap(context: Context, asset: String, targetWidth: Int): Bitmap? =
            withContext(Dispatchers.IO) {
                val key = "$asset@$targetWidth"
                bitmaps.get(key) ?: runCatching {
                    val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
                    context.assets.open(asset).use { BitmapFactory.decodeStream(it, null, bounds) }
                    var scale = 1
                    if (targetWidth > 0 && bounds.outWidth > 0) {
                        while (bounds.outWidth / (scale * 2) >= targetWidth) scale *= 2
                    }
                    val opts = BitmapFactory.Options().apply { inSampleSize = scale }
                    context.assets.open(asset).use {
                        BitmapFactory.decodeStream(it, null, opts)
                    }
                }.getOrNull()?.also { bitmaps.put(key, it) }
            }
    }
}
