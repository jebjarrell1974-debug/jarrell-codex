package org.jarrellcodex

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.material3.Surface
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.foundation.layout.fillMaxSize
import androidx.lifecycle.viewmodel.compose.viewModel
import org.jarrellcodex.ui.CodexTheme
import org.jarrellcodex.ui.ReaderScreen
import org.jarrellcodex.ui.ReaderViewModel

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            // The palette comes from what the reader chose, not from the
            // system's light/dark switch. Someone who needs high contrast
            // needs it in the evening too, and someone reading in bed with
            // the phone in light mode should still be able to pick Night.
            val vm = viewModel<ReaderViewModel>()
            val s by vm.state.collectAsState()
            CodexTheme(palette = s.palette, fontSize = s.fontSize) {
                Surface(Modifier.fillMaxSize()) {
                    ReaderScreen(vm)
                }
            }
        }
    }
}
