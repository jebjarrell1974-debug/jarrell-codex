package org.jarrellcodex.data

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.DatabaseView
import androidx.room.Entity
import androidx.room.PrimaryKey
import java.io.File
import java.util.zip.GZIPInputStream

/**
 * The database is prebuilt by scripts/build_all.sh and shipped read-only.
 * Nothing in the app ever writes to it.
 *
 * It travels gzipped (64 MB) and Room expands it to ~226 MB in app storage on
 * first launch. That keeps the APK comfortably under Play's 500 MB base-module
 * limit with no asset pack and no first-run download, so the app works the
 * moment it is installed - on a plane, in a basement, on a handed-over phone
 * with no SIM.
 *
 * Entities are declared only to satisfy Room's compile-time schema check; the
 * rows themselves are read through CodexDao's explicit SQL.
 */
@Entity(tableName = "verse")
data class VerseEntity(
    @PrimaryKey val verse_key: String,
    val book: String?, val book_order: Int?, val chapter: Int?, val verse: Int?,
    val testament: String?, val alt_ref: String?,
)

@Database(
    entities = [VerseEntity::class],
    views = [],
    version = 1,
    exportSchema = false,
)
abstract class CodexDatabase : RoomDatabase() {
    abstract fun dao(): CodexDao

    companion object {
        private const val ASSET = "codex.db.gz"
        private const val NAME = "codex.db"
        @Volatile private var instance: CodexDatabase? = null

        fun get(context: Context): CodexDatabase =
            instance ?: synchronized(this) {
                instance ?: build(context.applicationContext).also { instance = it }
            }

        private fun build(context: Context): CodexDatabase =
            Room.databaseBuilder(context, CodexDatabase::class.java, NAME)
                // Room copies from this stream once, on first open.
                .createFromInputStream { GZIPInputStream(context.assets.open(ASSET)) }
                .fallbackToDestructiveMigration()   // prebuilt and read-only: just re-copy
                .setJournalMode(JournalMode.TRUNCATE)  // read-only; no WAL sidecar needed
                .build()

        /** True once the expanded database exists on disk. */
        fun isUnpacked(context: Context): Boolean =
            File(context.getDatabasePath(NAME).path).exists()
    }
}
