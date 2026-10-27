package org.jarrellcodex.data

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject

/**
 * Which public-domain reading covers a chapter, and where in it the chapter
 * probably starts.
 *
 * The index ships inside the app (97 KB) so the app always knows what exists
 * even with no signal. The audio itself does not: it streams from
 * archive.org, and every screen that offers it says so.
 *
 * Most LibriVox readings hold many chapters in one file - the complete-Bible
 * set runs 32 chapters of Psalms in a single track. Each file therefore
 * carries the chapters it covers, in canonical order, with each one's verse
 * count, so a reader asking for Psalm 23 can be put near Psalm 23 rather
 * than at Psalm 1 with half an hour of audio and no idea where to drag.
 */
data class Reading(
    val url: String,
    /** Chapter keys this one file covers, in reading order. */
    val covers: List<String>,
    /** Verse count of each covered chapter, same order. */
    val verses: List<Int>,
    /** Where the wanted chapter sits in [covers]. */
    val at: Int,
    val megabytes: Double,
    val sourceTitle: String,
    val sourcePage: String,
    val licence: String,
) {
    val alone: Boolean get() = covers.size == 1

    /**
     * Where the chapter starts, as a fraction of the file. An estimate from
     * verse counts and nothing more: no one recorded a timing for this, and
     * every screen that uses it says as much.
     */
    val fraction: Float
        get() {
            val total = verses.sum()
            if (total <= 0 || at <= 0) return 0f
            return verses.take(at).sum().toFloat() / total
        }
}

class AudioIndex private constructor(
    private val files: List<Entry>,
    private val where: Map<String, IntArray>,
) {
    class Entry(
        val url: String, val item: String, val mb: Double,
        val chapters: List<String>, val verses: List<Int>,
    )

    val chapterCount: Int get() = where.size
    val fileCount: Int get() = files.size

    fun reading(book: String, chapter: Int): Reading? {
        val p = where["$book.$chapter"] ?: return null
        val f = files.getOrNull(p[0]) ?: return null
        val src = sources[f.item] ?: Source("LibriVox", "", "")
        return Reading(
            url = f.url, covers = f.chapters, verses = f.verses, at = p[1],
            megabytes = f.mb, sourceTitle = src.title,
            sourcePage = src.page, licence = src.licence,
        )
    }

    private class Source(val title: String, val page: String, val licence: String)

    private var sources: Map<String, Source> = emptyMap()

    companion object {
        private const val ASSET = "audio.json"
        @Volatile private var cached: AudioIndex? = null

        /** Parsed once. A failure means no Listen control, never a crash. */
        suspend fun load(context: Context): AudioIndex? = withContext(Dispatchers.IO) {
            cached ?: runCatching {
                val raw = context.assets.open(ASSET).use { it.readBytes() }
                    .toString(Charsets.UTF_8)
                val o = JSONObject(raw)

                val fa = o.getJSONArray("files")
                val files = ArrayList<Entry>(fa.length())
                for (i in 0 until fa.length()) {
                    val f = fa.getJSONObject(i)
                    val ca = f.getJSONArray("ch")
                    val va = f.getJSONArray("vs")
                    val ch = ArrayList<String>(ca.length())
                    val vs = ArrayList<Int>(va.length())
                    for (k in 0 until ca.length()) ch.add(ca.getString(k))
                    for (k in 0 until va.length()) vs.add(va.getInt(k))
                    files.add(Entry(f.getString("u"), f.getString("item"),
                        f.optDouble("mb", 0.0), ch, vs))
                }

                val co = o.getJSONObject("chapters")
                val where = HashMap<String, IntArray>(co.length() * 2)
                for (key in co.keys()) {
                    val pair = co.getJSONArray(key)
                    where[key] = intArrayOf(pair.getInt(0), pair.getInt(1))
                }

                val so = o.getJSONObject("sources")
                val sources = HashMap<String, Source>(so.length() * 2)
                for (item in so.keys()) {
                    val s = so.getJSONObject(item)
                    // Same trap as the picture manifests: an explicit
                    // JSON null comes back from optString as the string
                    // "null", so ask isNull instead.
                    sources[item] = Source(
                        if (s.isNull("title")) "LibriVox" else s.optString("title", "LibriVox"),
                        if (s.isNull("page")) "" else s.optString("page", ""),
                        if (s.isNull("licence")) "" else s.optString("licence", ""),
                    )
                }

                AudioIndex(files, where).also { it.sources = sources }
            }.getOrNull()?.also { cached = it }
        }
    }
}
