package org.jarrellcodex.data

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import java.io.File
import java.util.zip.GZIPInputStream

/**
 * The commentators, in a database of their own.
 *
 * Six public-domain commentaries - Henry, the 1599 Geneva notes, Calvin,
 * Poole, Trapp and Spurgeon - 91,008 units covering 99.6% of verses. The file
 * ships inside the APK so it needs no connection, because the people this is
 * meant for may not have one. But it unpacks to 148 MB on top of the main
 * database's 456 MB, and a cheap phone does not always have 600 MB to spare.
 *
 * So the asset travels with the app and the reader decides whether to spend
 * the disk. Nothing here is required: every call returns an empty list when
 * the commentary has not been unpacked, and the rest of the app does not
 * change shape.
 *
 * Opened as a separate connection rather than ATTACHed. The main database is
 * opened read-only, and Android's execSQL refuses statements on a read-only
 * connection; a second connection is simpler than fighting that, and nothing
 * here needs a cross-database join - commentary is keyed by the same
 * verse_key string the caller already holds.
 */
object CommentaryDatabase {

    const val ASSET = "commentary.db.gz"
    private const val NAME = "commentary.db"

    /** Roughly what unpacking costs on disk. Shown before asking. */
    const val UNPACKED_BYTES = 148L * 1024 * 1024

    @Volatile private var db: SQLiteDatabase? = null

    fun isUnpacked(context: Context): Boolean =
        context.getDatabasePath(NAME).let { it.exists() && it.length() > 0 }

    /** True when the APK actually carries the asset. A build may omit it. */
    fun isAvailable(context: Context): Boolean =
        try {
            context.assets.open(ASSET).use { true }
        } catch (e: Exception) {
            false
        }

    /** Null when the reader has not added the commentators. Never throws for that. */
    fun openOrNull(context: Context): SQLiteDatabase? {
        db?.let { return it }
        if (!isUnpacked(context)) return null
        return synchronized(this) {
            db ?: openExisting(context.applicationContext).also { db = it }
        }
    }

    private fun openExisting(context: Context): SQLiteDatabase =
        SQLiteDatabase.openDatabase(
            context.getDatabasePath(NAME).path, null,
            SQLiteDatabase.OPEN_READONLY or SQLiteDatabase.NO_LOCALIZED_COLLATORS,
        )

    /**
     * Expands the asset. Blocks; call off the main thread. Reports progress as
     * a fraction of the expected size so a 148 MB wait does not look frozen.
     *
     * Unpacks to a temporary file and renames, so a kill partway through
     * cannot leave something that looks complete and fails later in a more
     * confusing place.
     */
    fun unpack(context: Context, onProgress: (Float) -> Unit = {}): Boolean {
        if (isUnpacked(context)) return true
        val app = context.applicationContext
        val target = app.getDatabasePath(NAME)
        target.parentFile?.mkdirs()
        val tmp = File(target.parentFile, "$NAME.part")
        if (tmp.exists()) tmp.delete()
        return try {
            GZIPInputStream(app.assets.open(ASSET)).use { input ->
                tmp.outputStream().use { out ->
                    val buf = ByteArray(1 shl 16)
                    var total = 0L
                    while (true) {
                        val n = input.read(buf)
                        if (n < 0) break
                        out.write(buf, 0, n)
                        total += n
                        onProgress((total.toFloat() / UNPACKED_BYTES).coerceIn(0f, 1f))
                    }
                }
            }
            if (!tmp.renameTo(target)) {
                tmp.delete()
                false
            } else {
                onProgress(1f)
                true
            }
        } catch (e: Exception) {
            tmp.delete()
            false
        }
    }

    /** Gives the disk back. The asset stays in the APK, so this is reversible. */
    fun remove(context: Context): Boolean {
        synchronized(this) {
            db?.close()
            db = null
        }
        val f = context.applicationContext.getDatabasePath(NAME)
        return if (f.exists()) f.delete() else true
    }
}
