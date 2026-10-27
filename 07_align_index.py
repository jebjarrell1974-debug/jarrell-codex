"""Resolve translation verses to canonical keys via TVTMS, then build indexes."""
import sqlite3
DB="/home/claude/bible/build/bible.db"
db=sqlite3.connect(DB)

cols=[r[1] for r in db.execute("PRAGMA table_info(translation_verse)")]
if "canonical_key" not in cols:
    db.execute("ALTER TABLE translation_verse ADD COLUMN canonical_key TEXT")

# 1. direct hit: the KJV-numbered ref already is a canonical verse
db.execute("""UPDATE translation_verse SET canonical_key=verse_key
              WHERE EXISTS(SELECT 1 FROM verse v WHERE v.verse_key=translation_verse.verse_key)""")
# 2. otherwise map English(KJV) ref -> source-tradition ref used by our canonical text
db.execute("""UPDATE translation_verse SET canonical_key=(
                SELECT vm.tradition_ref FROM versification vm
                JOIN verse v ON v.verse_key=vm.tradition_ref
                WHERE vm.english_ref=translation_verse.verse_key LIMIT 1)
              WHERE canonical_key IS NULL""")
db.commit()

tot=db.execute("SELECT COUNT(*) FROM translation_verse").fetchone()[0]
ok=db.execute("SELECT COUNT(*) FROM translation_verse WHERE canonical_key IS NOT NULL").fetchone()[0]
print(f"translation verses aligned: {ok:,}/{tot:,} ({100*ok/tot:.3f}%)")
for r in db.execute("""SELECT code, verse_key FROM translation_verse
                       WHERE canonical_key IS NULL LIMIT 6"""): print("   unaligned:", r)

db.executescript("""
CREATE INDEX IF NOT EXISTS ix_token_verse     ON token(verse_key, position);
CREATE INDEX IF NOT EXISTS ix_token_lang      ON token(language);
CREATE INDEX IF NOT EXISTS ix_morph_token     ON morpheme(token_id, seq);
CREATE INDEX IF NOT EXISTS ix_morph_strongs   ON morpheme(strongs);
CREATE INDEX IF NOT EXISTS ix_morph_simple    ON morpheme(strongs_simple);
CREATE INDEX IF NOT EXISTS ix_morph_code      ON morpheme(morph_code);
CREATE INDEX IF NOT EXISTS ix_tv_canon        ON translation_verse(canonical_key, code);
CREATE INDEX IF NOT EXISTS ix_verse_order     ON verse(book_order, chapter, verse);
CREATE INDEX IF NOT EXISTS ix_lex_estrong     ON lexicon(estrong);
""")
db.commit()
db.execute("VACUUM"); db.execute("ANALYZE"); db.commit()
import os
print(f"database size: {os.path.getsize(DB)/1e6:.1f} MB")
db.close()
