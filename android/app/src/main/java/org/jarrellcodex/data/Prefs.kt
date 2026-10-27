package org.jarrellcodex.data

import android.content.Context
import org.jarrellcodex.ui.FS_DEFAULT
import org.jarrellcodex.ui.FS_MAX
import org.jarrellcodex.ui.FS_MIN
import org.jarrellcodex.ui.Palette

/**
 * What the reader chose, kept across launches.
 *
 * A reader who has set the text to 30sp has done so because they need it.
 * Making them do it again on every launch would be worse than not offering
 * the setting at all.
 */
class Prefs(context: Context) {

    private val sp = context.applicationContext
        .getSharedPreferences("codex", Context.MODE_PRIVATE)

    var fontSize: Int
        get() = sp.getInt(KEY_FS, FS_DEFAULT).coerceIn(FS_MIN, FS_MAX)
        set(v) { sp.edit().putInt(KEY_FS, v.coerceIn(FS_MIN, FS_MAX)).apply() }

    var palette: Palette
        get() = runCatching { Palette.valueOf(sp.getString(KEY_SCHEME, null) ?: "") }
            .getOrDefault(Palette.PAPER)
        set(v) { sp.edit().putString(KEY_SCHEME, v.name).apply() }

    var translation: String
        get() = sp.getString(KEY_TX, "KJV") ?: "KJV"
        set(v) { sp.edit().putString(KEY_TX, v).apply() }

    /**
     * Which chronology the reader prefers - Jones, Ussher and the rest.
     * Named apart from [palette] on purpose: the website had both meanings
     * on one key, and picking a colour there silently emptied the timeline.
     */
     var chronology: String
        get() = sp.getString(KEY_CHRON, "jones") ?: "jones"
        set(v) { sp.edit().putString(KEY_CHRON, v).apply() }

    /** Where the reader was, so the app opens there rather than at Genesis. */
    var lastBook: String
        get() = sp.getString(KEY_BOOK, "Gen") ?: "Gen"
        set(v) { sp.edit().putString(KEY_BOOK, v).apply() }

    var lastChapter: Int
        get() = sp.getInt(KEY_CH, 1)
        set(v) { sp.edit().putInt(KEY_CH, v).apply() }

    private companion object {
        const val KEY_FS = "fontSize"
        const val KEY_SCHEME = "scheme"
        const val KEY_TX = "translation"
        const val KEY_CHRON = "chronology"
        const val KEY_BOOK = "book"
        const val KEY_CH = "chapter"
    }
}
