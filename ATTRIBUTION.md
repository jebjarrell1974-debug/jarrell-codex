# Attribution and data licences

This project is assembled almost entirely from scholarly datasets that other
people made and gave away. Those licences require attribution, and this file
is that attribution. **It must ship with the app and travel with any copy of
the data.**

## Required attribution — show this in the application

> Hebrew, Greek and lexical data created by **STEPBible.org** based on work at
> **Tyndale House, Cambridge** (CC BY 4.0).
> Syntax and linguistic data from **Clear Bible, Inc.** — MACULA (CC BY 4.0).
> Place data from **OpenBible.info** Bible Geocoding Data (CC BY 4.0).
> People, events and dictionary data from **Theographic Bible Metadata**.

## Sources

| Dataset | Supplies | Licence |
|---|---|---|
| STEPBible TAHOT | Hebrew Old Testament, word level | CC BY 4.0 |
| STEPBible TAGNT | Greek New Testament, word level | CC BY 4.0 |
| STEPBible TBESH / TBESG | Hebrew and Greek lexicons | CC BY 4.0 |
| STEPBible TEHMC / TEGMC | Morphology code expansions | CC BY 4.0 |
| STEPBible TVTMS | Versification traditions | CC BY 4.0 |
| STEPBible TIPNR | Disambiguated proper names | CC BY 4.0 |
| MACULA Hebrew / Greek (Clear Bible) | Independent cross-check | CC BY 4.0 |
| OpenScriptures WLC (via MACULA) | Independent cross-check | CC BY 4.0 |
| OpenBible.info Bible Geocoding Data | Places, coordinates, confidence | CC BY 4.0 |
| Theographic Bible Metadata | People, events timeline, Easton's dictionary | CC BY-SA 4.0 |
| Easton's Bible Dictionary (1897) | Dictionary entries | Public domain |
| KJV, ASV, Darby, Young's Literal | English translations | Public domain |

## Obligations to keep in mind

- **Attribution is not optional.** CC BY requires crediting the source. The
  block above satisfies it; keep it visible in the app, not buried.
- **STEPBible asks that you point people to github.com/STEPBible for the data
  rather than redistributing it yourself.** This build clones from source at
  build time rather than vendoring their files, which respects that.
- **Share-alike spreads.** Anything brought in under CC BY-SA — unfoldingWord
  translation notes, Perseus LSJ — obliges derivative work under the same
  licence for the DATA. That is a deliberate choice and is independent of the
  code licence, but it is a one-way door.
- **Audio is not in this repository.** Faith Comes By Hearing's Bible Brain
  conditions its key on end users accessing content completely free of charge
  and on operating in accordance with their Statement of Faith. Read the DBP
  License before integrating it.
- **Modern translations are not here and mostly cannot be.** ESV, NIV, NASB
  and CSB are individually licensed and rarely granted to independent
  projects. The public-domain pool is what this is built on, by necessity and
  by design.
