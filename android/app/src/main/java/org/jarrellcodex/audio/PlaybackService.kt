package org.jarrellcodex.audio

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import org.jarrellcodex.MainActivity

/**
 * Keeps a reading going when the app is not in front.
 *
 * Someone listening to a chapter puts the phone down, and Android is
 * entitled to kill the process the moment nothing is on screen. A
 * foreground service with a notification is how you ask it not to. The
 * notification is also the only control a listener has once the screen is
 * off, so it carries pause and stop rather than being a bare placeholder.
 *
 * The service does not own the player - [Playback] does. This exists only
 * to keep the process alive and to put the controls in the shade. If it
 * cannot start, the audio still plays; it just may not outlive the app, and
 * [Playback] says so rather than letting the reader find out by surprise.
 */
class PlaybackService : Service() {

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_TOGGLE -> Playback.toggle()
            ACTION_STOP -> {
                Playback.stop(this)
                stopSelf()
                return START_NOT_STICKY
            }
        }
        runCatching { startForeground(ID, build()) }
            .onFailure { stopSelf() }
        return START_STICKY
    }

    private fun build(): Notification {
        val s = Playback.state.value
        val r = s.reading
        val title = if (s.chapterKey.isNotEmpty())
            s.chapterKey.replace('.', ' ') else "The Jarrell Codex"
        val body = when {
            s.preparing -> "Opening the reading…"
            r != null && !r.alone ->
                "Inside a reading of ${span(r.covers)}"
            else -> "A reading from LibriVox"
        }

        channel()
        val open = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)

        val b = Notification.Builder(this, CHANNEL)
            .setContentTitle(title)
            .setContentText(body)
            .setSmallIcon(android.R.drawable.ic_media_play)
            .setContentIntent(open)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
        b.addAction(
            Notification.Action.Builder(
                null,
                if (s.playing) "Pause" else "Play",
                pending(ACTION_TOGGLE, 1),
            ).build())
        b.addAction(
            Notification.Action.Builder(null, "Stop", pending(ACTION_STOP, 2)).build())
        return b.build()
    }

    private fun pending(action: String, code: Int): PendingIntent {
        val i = Intent(this, PlaybackService::class.java).setAction(action)
        return PendingIntent.getService(
            this, code, i,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
    }

    private fun channel() {
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (nm.getNotificationChannel(CHANNEL) != null) return
        val c = NotificationChannel(
            CHANNEL, "Spoken readings", NotificationManager.IMPORTANCE_LOW)
        c.description = "Shows what is playing, and lets you pause it."
        c.setShowBadge(false)
        nm.createNotificationChannel(c)
    }

    companion object {
        private const val CHANNEL = "readings"
        private const val ID = 7
        const val ACTION_TOGGLE = "org.jarrellcodex.TOGGLE"
        const val ACTION_STOP = "org.jarrellcodex.STOP"

        /** "Genesis 1 - 14" from the chapter keys the file covers. */
        fun span(covers: List<String>): String {
            if (covers.isEmpty()) return ""
            val first = covers.first().replace('.', ' ')
            val last = covers.last().substringAfterLast('.')
            return if (covers.size == 1) first else "$first–$last"
        }
    }
}
