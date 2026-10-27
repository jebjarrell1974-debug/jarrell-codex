package org.jarrellcodex.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import org.jarrellcodex.data.ChronologyNote
import org.jarrellcodex.data.Scheme
import org.jarrellcodex.data.TranslationInfo

/**
 * Where all of this came from.
 *
 * Not decoration. Most of the data is CC BY or CC BY-SA, which requires the
 * attribution to travel with every copy. An app that shipped this material
 * with no way to see who made it would be breaking the terms it was given
 * under, and this is a project about not doing that.
 */
@Composable
fun AboutSheet(
    translations: List<TranslationInfo>,
    schemes: List<Scheme>,
    notes: List<ChronologyNote>,
) {
    Column(
        Modifier.fillMaxWidth().verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp).padding(bottom = 36.dp),
    ) {
        Text("About this Bible", fontWeight = FontWeight.SemiBold,
             style = MaterialTheme.typography.titleMedium)
        Spacer(Modifier.height(10.dp))
        Text(
            "Every word of the Hebrew, Aramaic and Greek carries its dictionary " +
                "number and its grammar. Tap a word for its parts, what each part " +
                "means, and how often it appears. Tap a marker under a verse for " +
                "the places, the people, the dating, the translators' notes, the " +
                "cross-references and the commentators. It costs nothing, it needs " +
                "no connection, and it does not watch you.",
            style = MaterialTheme.typography.bodyMedium, lineHeight = 21.sp,
        )

        Section("Why the dates disagree")
        notes.forEach { n ->
            Spacer(Modifier.height(10.dp))
            Text(n.heading, fontWeight = FontWeight.SemiBold,
                 style = MaterialTheme.typography.bodyMedium)
            Spacer(Modifier.height(4.dp))
            Text(n.body, style = MaterialTheme.typography.bodySmall, lineHeight = 19.sp)
        }

        Section("The chronologies on offer")
        schemes.forEach { s ->
            Spacer(Modifier.height(10.dp))
            Row {
                Text(s.name, fontWeight = FontWeight.SemiBold,
                     style = MaterialTheme.typography.bodyMedium)
                Spacer(Modifier.width(8.dp))
                Text(s.coverage, style = MaterialTheme.typography.labelSmall,
                     color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Text(s.summary, style = MaterialTheme.typography.bodySmall, lineHeight = 19.sp)
            if (s.source.isNotBlank()) {
                Text(s.source, style = MaterialTheme.typography.labelSmall,
                     color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }

        Section("Spoken readings")
        Spacer(Modifier.height(8.dp))
        Text(
            "Every chapter of all 66 books has a reading, behind the Listen " +
                "button at each end of the text. They are LibriVox recordings, " +
                "read by volunteers and released into the public domain.\n\n" +
                "They are the one thing here that is not inside the app. " +
                "2.5 GB of audio would treble the download, so the readings " +
                "stream from archive.org and need a connection. Everything " +
                "else \u2014 the text, the parsing, the lexicons, the " +
                "commentaries, the pictures \u2014 works with no signal at all.\n\n" +
                "Most readings hold several chapters in one file. Where that " +
                "happens the app puts you near the chapter you asked for, " +
                "worked out from verse counts rather than from a timing anyone " +
                "recorded, and says so every time.",
            style = MaterialTheme.typography.bodySmall, lineHeight = 19.sp,
        )

        Section("Pictures")
        Spacer(Modifier.height(8.dp))
        Text(
            "150 of Dor\u00e9's engravings sit at the verses they illustrate, and " +
                "307 places that are still there are photographed in the panel " +
                "that names them. Each picture carries its licence, its " +
                "photographer or engraver, and a link to where it came from.\n\n" +
                "A place with no photograph has none. Nothing stands in for it.",
            style = MaterialTheme.typography.bodySmall, lineHeight = 19.sp,
        )

        Section("Where it came from")
        SOURCES.forEach { (who, what) ->
            Spacer(Modifier.height(10.dp))
            Text(who, fontWeight = FontWeight.SemiBold,
                 style = MaterialTheme.typography.bodyMedium)
            Text(what, style = MaterialTheme.typography.bodySmall, lineHeight = 19.sp)
        }

        if (translations.isNotEmpty()) {
            Section("English translations")
            translations.forEach { t ->
                Spacer(Modifier.height(6.dp))
                Text("${t.name} — ${t.licence}",
                     style = MaterialTheme.typography.bodySmall)
            }
        }

        Section("Licence")
        Spacer(Modifier.height(8.dp))
        Text(
            "The code is MPL-2.0. The assembled data is CC BY-SA 4.0, because " +
                "unfoldingWord's notes are share-alike and that carries. Take it, " +
                "copy it, hand it out.\n\n" +
                "github.com/jebjarrell1974-debug/jarrell-codex",
            style = MaterialTheme.typography.bodySmall, lineHeight = 19.sp,
        )
        Spacer(Modifier.height(16.dp))
        Text("The Jarrell Codex", style = MaterialTheme.typography.labelSmall,
             color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun Section(title: String) {
    Spacer(Modifier.height(24.dp))
    Text(title, style = MaterialTheme.typography.labelSmall,
         color = MaterialTheme.colorScheme.onSurfaceVariant)
    HorizontalDivider(Modifier.padding(top = 6.dp))
}

private val SOURCES = listOf(
    "STEPBible — Tyndale House, Cambridge" to
        "TAHOT and TAGNT: the Hebrew and Greek with a dictionary number and a " +
        "grammar code on every word, including separate numbers for prefixes " +
        "and endings. CC BY 4.0.",
    "Brown-Driver-Briggs, Thayer, Abbott-Smith, Liddell-Scott-Jones" to
        "The lexicon entries behind each number. Public domain, via STEPBible " +
        "and the Perseus Digital Library.",
    "OpenBible.info" to
        "Place coordinates with an honest confidence figure, and the " +
        "cross-reference weights. CC BY 4.0.",
    "Theographic Bible Metadata" to
        "People, events, and Easton's Bible Dictionary. CC BY 4.0.",
    "unfoldingWord" to
        "Translation Notes — verse by verse on wording, idiom and " +
        "background. CC BY-SA 4.0.",
    "MACULA" to "Syntactic and semantic annotation of the original. CC BY 4.0.",
    "LibriVox, via archive.org" to
        "The spoken readings \u2014 every chapter of all 66 books, read by " +
        "volunteers and released into the public domain. Streamed, not stored " +
        "on this phone, so they need a connection even where the text does not.",
    "Wikimedia Commons and Wikidata" to
        "The photographs of the places. Each carries its own licence and " +
        "photographer where it appears; none were used that are not free to " +
        "pass on.",
    "Gustave Dor\u00e9, 1866" to
        "The 150 engravings set in the text. Dor\u00e9 died in 1883, so the plates " +
        "have been in the public domain for a century; these scans come from " +
        "Wikimedia Commons.",
    "Henry, the Geneva notes, Calvin, Poole, Trapp, Spurgeon" to
        "Six commentaries written between 1599 and 1885, all public domain. " +
        "Two larger collections were left out: one carries a fair-use notice " +
        "over excerpts still under copyright, the other dates its translations " +
        "as “19th-century and later”. Anything whose terms cannot be " +
        "stood behind does not belong in a Bible meant to be copied.",
)
