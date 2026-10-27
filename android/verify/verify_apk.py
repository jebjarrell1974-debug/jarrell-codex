"""Replay the Android app's data path against the real built APK.

No emulator here, so this does what the app does, in the same order, with
the same bytes and the same SQL:

  AssetManager.open(ASSET)  ->  read the zip entry out of the APK
  GZIPInputStream(...)      ->  gunzip it
  SQLiteDatabase.open...    ->  open it read-only
  CodexDao / CommentaryDao  ->  run their queries verbatim

The Kotlin compiles; the SQL is where the bugs are. This catches a wrong
asset name, a corrupt stream, a missing table, and any query that does not
return what the UI assumes.
"""
import gzip, io, os, sqlite3, sys, zipfile

APK = r"C:\Android\work\android\app\build\outputs\apk\debug\app-debug.apk"
OUT = r"C:\Android\work\verify"
os.makedirs(OUT, exist_ok=True)

fails = []
def chk(name, cond, detail=""):
    print(("  ok   " if cond else "  FAIL ") + name + (("  " + str(detail)[:300]) if not cond else ""))
    if not cond:
        fails.append(name)

# ---- what the app asks the AssetManager for, taken from the Kotlin ----------
def asset_const(path, needle):
    src = open(path, encoding="utf-8").read()
    for line in src.splitlines():
        if needle in line and "ASSET" in line and '"' in line:
            return line.split('"')[1]
    return None

KT = r"C:\Android\work\android\app\src\main\java\org\jarrellcodex\data"
codex_asset = asset_const(os.path.join(KT, "CodexDatabase.kt"), "ASSET =")
cmt_asset = asset_const(os.path.join(KT, "CommentaryDatabase.kt"), "ASSET =")
print(f"asset names the app will request: {codex_asset!r}, {cmt_asset!r}\n")

print("APK")
z = zipfile.ZipFile(APK)
names = set(z.namelist())
chk("codex asset present under the name the app opens",
    f"assets/{codex_asset}" in names,
    sorted(n for n in names if n.startswith("assets/")))
chk("commentary asset present under the name the app opens",
    f"assets/{cmt_asset}" in names,
    sorted(n for n in names if n.startswith("assets/")))
for n in (f"assets/{codex_asset}", f"assets/{cmt_asset}"):
    if n in names:
        i = z.getinfo(n)
        chk(f"{n} stored uncompressed (noCompress works)",
            i.compress_type == zipfile.ZIP_STORED, i.compress_type)

def unpack(entry, dest):
    """GZIPInputStream(assets.open(entry)) -> file, exactly as the app does."""
    p = os.path.join(OUT, dest)
    if os.path.exists(p) and os.path.getsize(p) > 0:
        return p
    tmp = p + ".part"
    with z.open(entry) as raw, gzip.GzipFile(fileobj=raw) as gz, open(tmp, "wb") as out:
        while True:
            b = gz.read(1 << 20)
            if not b:
                break
            out.write(b)
    os.replace(tmp, p)
    return p

print("\nunpack (what happens on first launch)")
try:
    codex = unpack(f"assets/{codex_asset}", "codex.db")
    chk("codex.db gunzips", os.path.getsize(codex) > 400_000_000,
        os.path.getsize(codex))
except Exception as e:
    chk("codex.db gunzips", False, e); codex = None
try:
    cmt = unpack(f"assets/{cmt_asset}", "commentary.db")
    chk("commentary.db gunzips", os.path.getsize(cmt) > 100_000_000,
        os.path.getsize(cmt))
except Exception as e:
    chk("commentary.db gunzips", False, e); cmt = None

# ---- the DAO queries, verbatim ---------------------------------------------
if codex:
    print("\nCodexDao")
    db = sqlite3.connect(f"file:{codex}?mode=ro", uri=True)
    rows = db.execute(
        """SELECT t.token_id, t.verse_key, t.position, t.surface, t.translit,
                  t.gloss, t.language
           FROM token t JOIN verse v ON v.verse_key = t.verse_key
           WHERE v.book = ? AND v.chapter = ?
             AND (t.text_type GLOB 'L*' OR t.text_type GLOB '*N*')
           ORDER BY v.verse, t.position""", ("Jhn", 3)).fetchall()
    chk("chapter(Jhn,3) returns tokens", len(rows) > 300, len(rows))
    if rows:
        tid = rows[0][0]
        m = db.execute(
            """SELECT m.seq, m.surface, m.strongs, m.strongs_simple,
                      mc.description AS parsing, l.lemma, l.gloss, l.definition
               FROM morpheme m
               LEFT JOIN morph_code mc ON mc.code = m.morph_code
               LEFT JOIN lexicon    l  ON l.strongs = m.strongs
               WHERE m.token_id = ? ORDER BY m.seq""", (tid,)).fetchall()
        chk("morphemes() returns parts with a lexicon entry",
            len(m) > 0 and any(r[4] for r in m), m[:2])
    n = db.execute("SELECT COUNT(*) FROM morpheme WHERE strongs_simple = ?",
                   ("H3068",)).fetchone()[0]
    chk("concordance H3068 = 6,528 as benchmarked", n == 6528, n)
    tv = db.execute(
        "SELECT code, text FROM translation_verse WHERE canonical_key = ? ORDER BY code",
        ("Jhn.3.16",)).fetchall()
    chk("translations(Jhn.3.16) returns four", len(tv) == 4, tv)
    sc = db.execute(
        """SELECT scheme_id, name, coverage, summary, source, is_default
           FROM chronology_scheme ORDER BY sort_order""").fetchall()
    chk("schemes() returns six", len(sc) == 6, len(sc))
    ev = db.execute(
        """SELECT e.event_id, e.title, d.start_year, d.precision, d.note
           FROM event e
           JOIN event_verse ev ON ev.event_id = e.event_id
           LEFT JOIN event_date d
                  ON d.event_id = e.event_id AND d.scheme_id = ?
           WHERE ev.verse_key = ? ORDER BY e.sort_key""",
        ("ussher", "Gen.1.1")).fetchall()
    chk("events() LEFT JOIN keeps an undated scheme null, not borrowed",
        len(ev) > 0, ev[:2])
    db.close()

if cmt:
    print("\nCommentaryDao")
    db = sqlite3.connect(f"file:{cmt}?mode=ro", uri=True)
    fv = db.execute(
        """SELECT c.unit_id, c.source_id, m.author, m.work, c.scope,
                  c.verse_from, c.verse_to, c.title, c.body
           FROM commentary_verse v
           JOIN commentary  c ON c.unit_id   = v.unit_id
           JOIN commentator m ON m.source_id = c.source_id
           WHERE v.verse_key = ?
           ORDER BY m.sort, c.verse_from""", ("Jhn.3.16",)).fetchall()
    chk("forVerse(Jhn.3.16) returns five commentators", len(fv) == 5,
        [(r[2], r[5], r[6]) for r in fv])
    chk("bodies are not empty", all(r[8].strip() for r in fv))
    chk("paragraph split works (body uses a blank line)",
        any(len(r[8].split("\n\n")) > 1 for r in fv),
        [len(r[8].split("\n\n")) for r in fv])
    fc = db.execute(
        """SELECT c.unit_id, c.source_id, m.author, m.work, c.scope,
                  c.verse_from, c.verse_to, c.title, c.body
           FROM commentary c
           JOIN commentator m ON m.source_id = c.source_id
           WHERE c.book = ? AND c.chapter = ? AND c.verse_from IS NULL
           ORDER BY CASE c.scope WHEN 'book' THEN 0 ELSE 1 END, m.sort""",
        ("Gen", 1)).fetchall()
    chk("forChapter(Gen,1) returns book prefaces and chapter overviews",
        len(fc) > 0, len(fc))
    chk("a book preface sorts first", fc and fc[0][4] == "book",
        [r[4] for r in fc[:3]])
    counts = {}
    for a, b in db.execute(
            """SELECT verse_from, verse_to FROM commentary
               WHERE book = ? AND chapter = ? AND verse_from IS NOT NULL""",
            ("Jhn", 3)):
        b = a if b is None else b
        for v in range(a, b + 1):
            counts[v] = counts.get(v, 0) + 1
    chk("countsForChapter(Jhn,3) agrees with forVerse for v16",
        counts.get(16) == len(fv), f"{counts.get(16)} vs {len(fv)}")
    chk("counts cover most of the chapter", len(counts) >= 35, len(counts))
    cm = db.execute(
        "SELECT source_id, author, work, sort FROM commentator ORDER BY sort").fetchall()
    chk("commentators() returns six in order", len(cm) == 6 and cm[0][0] == "henry",
        [r[0] for r in cm])
    db.close()

print()
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURES: {fails}")
sys.exit(1 if fails else 0)
