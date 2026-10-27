package org.jarrellcodex.data

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import java.io.File
import java.util.zip.GZIPInputStream

/**
 * The database is prebuilt by scripts/build_all.sh and shipped READ-ONLY.
 * Nothing in the app ever writes to it.
 *
 * Deliberately not Room. Room verifies every @Query against a schema it builds
 * from declared @Entity classes, which would mean restating all 19 tables just
 * to satisfy a compile-time check on a file that is generated, fixed, and
 * never migrated. Room's migration machinery is dead weight for a read-only
 * asset, and the entity declarations would be a second source of truth free to
 * drift from the real schema. Plain SQLite is less code and has no such drift.
 *
 * It travels gzipped (61 MB) and is expanded to ~226 MB in app storage on
 * first launch - inside Play's 500 MB base-module limit, so there is no asset
 * pack and no first-run download. The app works the moment it is installed.
 */
object CodexDatabase {

    private const val ASSET = "codex.db.gz"
    private const val NAME = "codex.db"
    @Volatile private var db: SQLiteDatabase? = null

    fun isUnpacked(context: Context): Boolean =
        context.getDatabasePath(NAME).let { it.exists() && it.length() > 0 }

    /** Blocks on first call while the database is expanded. Call off the main thread. */
    fun open(context: Context): SQLiteDatabase =
        db ?: synchronized(this) { db ?: unpackAndOpen(context.applicationContext).also { db = it } }

    private fun unpackAndOpen(context: Context): SQLiteDatabase {
        val target = context.getDatabasePath(NAME)
        if (!isUnpacked(context)) {
            target.parentFile?.mkdirs()
            // Expand to a temporary file first, then rename. A half-written
            // database left by a kill during unpacking would otherwise look
            // complete on the next launch and fail in a far more confusing way.
            val tmp = File(target.parentFile, "$NAME.part")
            if (tmp.exists()) tmp.delete()
            GZIPInputStream(context.assets.open(ASSET)).use { input ->
                tmp.outputStream().use { out -> input.copyTo(out, 1 shl 16) }
            }
            if (!tmp.renameTo(target)) {
                tmp.delete()
                error("Could not move the unpacked database into place")
            }
        }
        return SQLiteDatabase.openDatabase(
            target.path, null,
            SQLiteDatabase.OPEN_READONLY or SQLiteDatabase.NO_LOCALIZED_COLLATORS,
        )
    }
}
