package org.jarrellcodex.audio

import android.content.Context
import android.content.Intent
import android.media.AudioAttributes
import android.media.MediaPlayer
import android.os.Build
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import org.jarrellcodex.data.Reading

/**
 * One player for the whole app.
 *
 * A single owner, held outside any screen, because the reading has to
 * survive what the reader does next: a file covering Genesis 1 to 14 should
 * keep playing while they page through those chapters, and should not stop
 * because a sheet opened or the screen rotated.
 *
 * android.media.MediaPlayer rather than a media library: it is in the
 * framework, it streams HTTP, and it adds nothing to the download. The
 * trade is no gapless playback and no caching, neither of which matters for
 * one half-hour file at a time.
 */
object Playback {

    data class State(
        val reading: Reading? = null,
        /** The chapter the reader asked for, which may sit inside [reading]. */
        val chapterKey: String = "",
        val preparing: Boolean = false,
        val playing: Boolean = false,
        val positionMs: Int = 0,
        val durationMs: Int = 0,
        /** True while the position came from the verse-count estimate. */
        val estimated: Boolean = false,
        val estimatedMs: Int = 0,
        /** True when this reading started because the last one ended. */
        val continued: Boolean = false,
        val error: String? = null,
    ) {
        val open: Boolean get() = reading != null
    }

    private val _state = MutableStateFlow(State())
    val state: StateFlow<State> = _state.asStateFlow()

    private var mp: MediaPlayer? = null
    private var seekOnReady: Float? = null

    /**
     * Supplied by the view model so this object does not need to know how
     * the index is loaded. Given a chapter key, it starts that reading.
     */
    var onFinished: ((Context) -> Unit)? = null

    /**
     * Start, or re-label without restarting.
     *
     * Asking for a chapter already inside the file being played only changes
     * what the bar says. Restarting the file would throw away the reader's
     * place for no reason.
     */
    fun open(context: Context, key: String, r: Reading, continued: Boolean = false) {
        val app = context.applicationContext
        val cur = _state.value
        if (cur.reading?.url == r.url && mp != null) {
            _state.value = cur.copy(reading = r, chapterKey = key, error = null)
            return
        }
        release()
        _state.value = State(reading = r, chapterKey = key, preparing = true,
                             continued = continued)
        seekOnReady = if (r.alone || r.at == 0) null else r.fraction

        val player = MediaPlayer()
        mp = player
        runCatching {
            player.setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_MEDIA)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                    .build()
            )
            @Suppress("DEPRECATION")
            player.setWakeMode(app, android.os.PowerManager.PARTIAL_WAKE_LOCK)
            player.setOnPreparedListener { onReady(app, it) }
            // A reading that stops dead at the end of Genesis 14 and waits
            // to be asked is not much use to someone listening with the
            // phone face down. The files run end to end through the whole
            // canon, so carry on into the next one.
            player.setOnCompletionListener {
                _state.value = _state.value.copy(playing = false)
                onFinished?.invoke(app)
            }
            player.setOnErrorListener { _, what, extra ->
                _state.value = _state.value.copy(
                    preparing = false, playing = false,
                    error = "The reading would not play ($what/$extra). " +
                            "It streams from archive.org, so it needs a connection.",
                )
                true
            }
            player.setDataSource(r.url)
            player.prepareAsync()
        }.onFailure { e ->
            _state.value = _state.value.copy(
                preparing = false,
                error = "The reading would not start: " +
                        (e.message ?: e.javaClass.simpleName),
            )
            release()
        }
    }

    private fun onReady(app: Context, player: MediaPlayer) {
        val dur = runCatching { player.duration }.getOrDefault(0)
        var est = 0
        val f = seekOnReady
        if (f != null && dur > 0) {
            est = (dur * f).toInt()
            runCatching { player.seekTo(est) }
        }
        seekOnReady = null
        runCatching { player.start() }
        _state.value = _state.value.copy(
            preparing = false, playing = true, durationMs = dur,
            positionMs = est, estimated = est > 0, estimatedMs = est,
        )
        // Only once something is actually playing is a foreground service
        // honest about what it is for.
        startService(app)
    }

    fun toggle() {
        val player = mp ?: return
        runCatching {
            if (player.isPlaying) { player.pause(); _state.value = _state.value.copy(playing = false) }
            else { player.start(); _state.value = _state.value.copy(playing = true) }
        }
    }

    fun seekTo(ms: Int) {
        val player = mp ?: return
        runCatching { player.seekTo(ms.coerceAtLeast(0)) }
        _state.value = _state.value.copy(positionMs = ms, estimated = false)
    }

    /** Back to the start of the file, which is where the estimate came from. */
    fun restart() {
        seekTo(0)
    }

    fun skip(ms: Int) {
        val player = mp ?: return
        val to = (runCatching { player.currentPosition }.getOrDefault(0) + ms)
            .coerceIn(0, _state.value.durationMs.coerceAtLeast(0))
        seekTo(to)
    }

    /** Called from the UI on a timer; the player is the only truth here. */
    fun tick() {
        val player = mp ?: return
        val pos = runCatching { player.currentPosition }.getOrDefault(-1)
        if (pos >= 0 && pos != _state.value.positionMs) {
            _state.value = _state.value.copy(positionMs = pos)
        }
    }

    fun stop(context: Context) {
        release()
        _state.value = State()
        runCatching {
            context.applicationContext.stopService(
                Intent(context.applicationContext, PlaybackService::class.java))
        }
    }

    private fun release() {
        val player = mp
        mp = null
        seekOnReady = null
        runCatching { player?.reset() }
        runCatching { player?.release() }
    }

    private fun startService(app: Context) {
        runCatching {
            val i = Intent(app, PlaybackService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) app.startForegroundService(i)
            else app.startService(i)
        }
        // A refused service is not a reason to stop the audio. It only means
        // playback may not survive the app going to the background, so say so
        // rather than pretending nothing happened.
        .onFailure {
            _state.value = _state.value.copy(
                error = "Playing, but this reading may stop if you leave the app.")
        }
    }
}
