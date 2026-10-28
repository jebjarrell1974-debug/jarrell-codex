/* The Jarrell Codex — offline-capable study reader.
   MPL-2.0. Data credits in the About panel. */
'use strict';

const D = 'data/';
const S = {
  books: [], names: {}, bookIx: {},
  morph: {}, chron: null, order: null,
  place: null, person: null, event: null, dictIx: null, cmMeta: null, pix: null,
  man: null, dlTiers: {}, dore: null, showPix: true, audio: null,
  pano: null,
  fs: 19, scheme: 'paper', schemes: null,
  lex: {}, conc: {}, idx: {},
  book: 'Jhn', ch: 3,
  tx: 'KJV', chrono: 'jones', showOrig: true, pron: 'erasmian'
};
const TX = {
  KJV: 'King James Version (1769)',
  ASV: 'American Standard Version (1901)',
  YLT: "Young's Literal Translation (1862/98)",
  Darby: 'Darby Translation (1890)'
};
const $ = s => document.querySelector(s);
const esc = t => String(t == null ? '' : t)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;');

/* ---------------------------------------------------------------- fetching */
const memo = new Map();
async function get(path) {
  if (memo.has(path)) return memo.get(path);
  const p = fetch(D + path).then(r => {
    if (!r.ok) throw new Error(path + ' ' + r.status);
    return r.json();
  }).catch(e => { memo.delete(path); throw e; });
  memo.set(path, p);
  return p;
}
const bucket = s => {
  const m = /^([HGA])(\d+)/.exec(s || '');
  return m ? m[1] + ('0000' + m[2]).slice(-4).slice(0, 2) : 'XX';
};
const shard2 = t => { const k = (t || '').replace(/[^a-z]/g, '').slice(0, 2);
                      return k ? (k + 'zz').slice(0, 2) : 'xx'; };

// null = no such entry; OFFLINE = we could not reach the file at all.
const OFFLINE = Symbol('offline');
async function lex(strongs) {
  const b = bucket(strongs);
  if (!S.lex[b]) {
    try { S.lex[b] = await get(`lex/${b}.json`); }
    catch { return OFFLINE; }
  }
  return S.lex[b][strongs] || null;
}
async function conc(strongs) {
  const b = bucket(strongs);
  if (!S.conc[b]) {
    try { S.conc[b] = await get(`conc/${b}.json`); }
    catch { return OFFLINE; }
  }
  return S.conc[b][strongs] || null;
}
async function idx(kind, term) {
  const key = kind + '/' + shard2(term);
  if (!S.idx[key]) { try { S.idx[key] = await get(`idx/${key}.json`); }
                     catch { S.idx[key] = {}; } }
  return S.idx[key][term] || null;
}
/* Always a promise, even when the answer is already in memory.
   `S.pix || get(...)` returns the bare object on the second call, and
   `lazy.pix().catch(...)` then throws TypeError: .catch is not a function
   - which took out the whole place panel from the second place a reader
   tapped onwards, because the thrown error left the sheet showing
   whatever had been in it before. It shipped that way and nothing caught
   it, because every test only ever opened one place. */
const lazily = (key, file) => () =>
  S[key] != null ? Promise.resolve(S[key])
                 : get(file).then(d => (S[key] = d));
const lazy = {
  place: lazily('place', 'place.json'),
  person: lazily('person', 'person.json'),
  event: lazily('event', 'event.json'),
  dictIx: lazily('dictIx', 'dict_index.json'),
  cmMeta: lazily('cmMeta', 'commentary.json'),
  pix: lazily('pix', 'pix_manifest.json'),
  dore: lazily('dore', 'dore.json'),
  audio: lazily('audio', 'audio.json'),
  pano: lazily('pano', 'pano.json')
};

/* ------------------------------------------------------------- references */
// names[code] is [code, full, abbrev...]. Job carries only its code, because
// the source lists no separate full name for a book already called Job - so
// take the first entry that exists instead of assuming index 1 is there.
// Without this every reference in Job renders as "undefined 1".
function bookName(code) {
  const nm = S.names[code];
  return (nm && (nm[1] || nm[0])) || code;
}
function refLabel(vk) {
  const p = String(vk).split('.');
  return bookName(p[0]) + ' ' + (p[1] || '') + (p[2] ? ':' + p[2] : '');
}
function parseRef(text) {
  const m = /^\s*((?:[1-3]|i{1,3}|first|second|third)?\s*[a-z. ]+?)\s*(\d+)?(?:\s*[:.]\s*(\d+))?\s*$/i
    .exec(text || '');
  if (!m) return null;
  const want = m[1].toLowerCase().replace(/[.\s]+/g, ' ').trim();
  let hit = null;
  for (const code in S.names) {
    for (const n of S.names[code]) {
      const c = n.toLowerCase().replace(/[.\s]+/g, ' ').trim();
      if (c === want) { hit = code; break; }
      if (!hit && c.startsWith(want) && want.length >= 3) hit = code;
    }
    if (hit === code) break;
  }
  if (!hit) return null;
  return { book: hit, ch: m[2] ? +m[2] : 1, v: m[3] ? +m[3] : null };
}

/* ------------------------------------------------------------- morphology */
function parseMorph(code) {
  if (!code) return null;
  const raw = S.morph[code];
  if (raw) return raw.split(';').map(s => s.trim()).filter(Boolean);
  return null;
}
function roleOf(code) {
  const p = parseMorph(code);
  if (!p) return null;
  const f = p.find(x => /^Function=/.test(x));
  return f ? f.split('=')[1].trim().toLowerCase() : null;
}

/* ------------------------------------------------- Greek pronunciation */
const PRON = {
  erasmian: 'Erasmian — the classroom convention in most English-speaking seminaries. Not how any native speaker ever spoke, but it keeps the letters distinct, which is why it is taught.',
  modern: 'Modern Greek — how the text is read aloud in Greece today, and in the Greek Orthodox Church. β is "v", αι is "e", οι and υ and ει all collapse to "ee".',
  koine: 'Reconstructed Koine — scholars’ best estimate of first-century pronunciation, built from spelling mistakes in papyri. Sits between the other two.'
};
const PRON_MAP = {
  modern: [[/ai/g,'e'],[/oi/g,'i'],[/ei/g,'i'],[/ou/g,'u'],[/eu/g,'ev'],
           [/au/g,'av'],[/b/g,'v'],[/\bth/g,'th'],[/y/g,'i'],[/ē/g,'i'],[/ō/g,'o']],
  koine: [[/ai/g,'e'],[/oi/g,'y'],[/ei/g,'i'],[/ou/g,'u'],[/b/g,'b'],[/ē/g,'ē']],
  erasmian: []
};
function pronounce(tr, langTag) {
  if (langTag !== 'G' || S.pron === 'erasmian') return tr;
  let out = String(tr);
  for (const [re, rep] of PRON_MAP[S.pron] || []) out = out.replace(re, rep);
  return out;
}

/* ============================================================ the reader */
let CH = null;                       // chapter currently rendered

async function openChapter(book, ch, scrollToVerse) {
  const meta = S.bookIx[book];
  if (!meta) return;
  ch = Math.max(1, Math.min(ch | 0 || 1, meta.chapters));
  S.book = book; S.ch = ch;
  $('#ref').textContent = refLabel(book + '.' + ch);
  $('#view').innerHTML = '<p class="load">Loading…</p>';
  let d;
  if (S.showPix && !S.dore) await lazy.dore().catch(() => { S.dore = null; });
  try { d = await get(`ch/${book}.${ch}.json`); }
  catch {
    $('#view').innerHTML = `<p class="load">That chapter would not load.
      If you are offline, chapters you have already opened still work.</p>`;
    return;
  }
  CH = d;
  renderChapter(scrollToVerse);
}

function renderChapter(scrollToVerse) {
  if (!CH) return;
  const d = CH, out = [];
  const rtl = d.v.some(v => (v.t || []).some(t => t[4] === 'H'));
  out.push(`<h1 style="font-size:1.35rem;margin:6px 0 2px">${esc(refLabel(d.b + '.' + d.c))}</h1>`);
  out.push(`<p class="ot" style="margin:0 0 14px">${rtl ? 'Hebrew / Aramaic' : 'Greek'}
    &middot; ${esc(TX[S.tx] || S.tx)}</p>`);
  out.push(`<button class="listen" data-listen="1">
    <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M8 5v14l11-7z"/></svg>
    <span>Listen to this chapter</span></button>`);

  d.v.forEach((v, vi) => {
    out.push(`<div class="v" id="v${v.n}">`);
    let para = false;
    if (S.showOrig && v.t && v.t.length) {
      const lang = v.t[0][4] === 'H' ? 'heb' : 'grk';
      out.push(`<div class="orig"${lang === 'heb' ? ' dir="rtl"' : ''}>`);
      v.t.forEach((t, ti) => {
        const role = (v.sr || {})[String(t[0])] || '';
        const cls = 'w ' + lang + (role === 'verb' ? ' role-verb' : '');
        // the source glues a pilcrow to the last word of a paragraph
        const face = String(t[1]).replace(/\u00b6/g, '');
        if (/\u00b6/.test(t[1])) para = true;
        out.push(`<button class="${cls}" data-v="${vi}" data-t="${ti}"
          aria-label="${esc(face)}, ${esc(t[3] || '')}">${esc(face)}</button>`);
      });
      out.push('</div>');
    }
    const txt = (v.x || {})[S.tx] || (v.x || {}).KJV || '';
    out.push(`<div class="eng"><span class="vnum">${v.n}</span>${esc(txt)}</div>`);

    const ch = [];
    (v.p || []).forEach((p, i) => ch.push(
      `<button class="chip place" data-k="place" data-v="${vi}" data-i="${i}">◆ ${esc(p[0])}</button>`));
    (v.pe || []).forEach((p, i) => ch.push(
      `<button class="chip person" data-k="person" data-v="${vi}" data-i="${i}">${esc(p)}</button>`));
    (v.ev || []).forEach((e, i) => ch.push(
      `<button class="chip event" data-k="event" data-v="${vi}" data-i="${i}">⧖ ${esc(e[1])}</button>`));
    if ((v.nt || []).length) ch.push(
      `<button class="chip note" data-k="note" data-v="${vi}">✎ ${v.nt.length} note${v.nt.length > 1 ? 's' : ''}</button>`);
    if ((v.xr || []).length) ch.push(
      `<button class="chip xr" data-k="xref" data-v="${vi}">⇄ ${v.xr.length} cross-ref${v.xr.length > 1 ? 's' : ''}</button>`);
    if (v.cm) ch.push(
      `<button class="chip cm" data-k="cm" data-v="${vi}">§ ${v.cm} commentar${v.cm > 1 ? 'ies' : 'y'}</button>`);
    if (ch.length) out.push(`<div class="chips">${ch.join('')}</div>`);
    out.push('</div>');
    if (para) out.push('<div class="para" aria-hidden="true"></div>');
    if (S.showPix && S.dore) {
      ((S.dore.at || {})[`${d.b}.${d.c}.${v.n}`] || []).forEach(pid => {
        const pl = (S.dore.plates || {})[pid];
        if (!pl) return;
        out.push(`<figure class="plate">
          <img src="data/dore/${esc(pl.file)}" alt="${esc(pl.title)}, engraved by Gustave Dor\u00e9"
            width="${pl.w}" height="${pl.h}" loading="lazy" decoding="async">
          <figcaption>${esc(pl.title)}${
            pl.ref ? ` <span class="ot">${esc(pl.ref)}</span>` : ''}
            <span class="ot" style="display:block;margin-top:3px">Gustave Dor\u00e9, 1866${
            pl.page ? ` \u00b7 <a href="${esc(pl.page)}" target="_blank" rel="noopener">source</a>` : ''
            }</span></figcaption></figure>`);
      });
    }
  });

  if (d.cmc) out.push(`<div style="margin:20px 0 0"><button class="chip cm"
    data-k="cmch" style="min-height:44px;padding:8px 14px">\u00a7 Commentary on
    ${esc(refLabel(d.b + '.' + d.c)).replace(/ \d+$/, '')} and this chapter</button></div>`);

  const meta = S.bookIx[d.b];
  out.push(`<button class="listen" data-listen="1" style="margin:22px 0 0">
    <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M8 5v14l11-7z"/></svg>
    <span>Listen to ${esc(refLabel(d.b + '.' + d.c))}</span></button>`);
  out.push(`<div style="display:flex;gap:10px;margin:22px 0 0">
    ${d.c > 1 ? `<button class="chip" data-nav="prev" style="flex:1;justify-content:center;min-height:${44}px">← ${esc(refLabel(d.b + '.' + (d.c - 1)))}</button>` : ''}
    ${d.c < meta.chapters ? `<button class="chip" data-nav="next" style="flex:1;justify-content:center;min-height:44px">${esc(refLabel(d.b + '.' + (d.c + 1)))} →</button>` : ''}
  </div>`);
  out.push(footer());
  $('#view').innerHTML = out.join('');
  if (scrollToVerse) {
    const el = $('#v' + scrollToVerse);
    if (el) el.scrollIntoView({ block: 'center' });
  } else window.scrollTo(0, 0);
}

function footer() {
  return `<div class="foot">
    Original-language text and parsing: STEPBible TAHOT / TAGNT (CC BY 4.0).
    Lexicons: Brown-Driver-Briggs, Thayer, Abbott-Smith, Liddell-Scott-Jones.
    Places: OpenBible.info. People, events and dictionary: Theographic Bible
    Metadata (Easton's). Translation notes: unfoldingWord (CC BY-SA 4.0).
    Commentary: Matthew Henry, the Geneva notes, Calvin, Poole, Trapp and Spurgeon.
    Cross-references: Treasury of Scripture Knowledge via OpenBible.
    Spoken readings: LibriVox, streamed from archive.org.
    Photographs: Wikimedia Commons. Engravings: Gustave Doré, 1866.
    Translations, commentaries and readings are public domain.
    <button data-go="about" style="color:var(--accent);padding:8px 0;display:block">
      Full sources, licences, and how to read the chronologies →</button>
  </div>`;
}

/* ============================================================== the sheet */
function sheet(html) {
  $('#sheet').innerHTML =
    '<div class="sheet-top"><div class="grab"></div>' +
    '<button class="sheet-x" data-close="1" aria-label="Close">\u2715</button></div>' + html;
  $('#sheet').classList.add('open');
  $('#scrim').classList.add('open');
  $('#sheet').scrollTop = 0;
}
function closeSheet() {
  $('#sheet').classList.remove('open');
  $('#scrim').classList.remove('open');
}

/* -------------------------------------------------------- word study */
async function wordSheet(vi, ti) {
  const v = CH.v[vi], t = v.t[ti];
  const lang = t[4] === 'H' ? 'heb' : 'grk';
  const langName = t[4] === 'H' ? 'Hebrew / Aramaic' : 'Greek';
  const o = [];
  o.push(`<p class="lbl">${esc(refLabel(CH.b + '.' + CH.c + '.' + v.n))} &middot; word ${t[0]} &middot; ${langName}</p>`);
  o.push(`<div class="hw"><span class="big ${lang}">${esc(String(t[1]).replace(/\u00b6/g, ''))}</span>
    <span class="tr">${esc(pronounce(t[2], t[4]))}</span></div>`);
  if (t[3]) o.push(`<p class="de" style="font-weight:600">“${esc(t[3])}”</p>`);
  const role = (v.sr || {})[String(t[0])];
  if (role) o.push(`<p class="oc">role in the clause: ${esc(role)}</p>`);
  if (t[4] === 'G' && S.pron !== 'erasmian')
    o.push(`<p class="oc">pronunciation: ${esc(S.pron)}</p>`);

  const parts = t[5] || [];
  if (parts.length > 1)
    o.push(`<p class="lbl" style="margin:16px 0 0">${parts.length} parts — this one
      word carries a prefix, root and ending, each with its own number</p>`);

  o.push('<div id="morphs">');
  parts.forEach((m, mi) => {
    const g = parseMorph(m[1]);
    o.push(`<div class="mo"><div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
      <span class="sn">${esc(m[2] || m[0])}</span>
      ${m[0] !== m[2] ? `<span class="ot">extended ${esc(m[0])}</span>` : ''}
      ${m[1] ? `<span class="ot">${esc(m[1])}</span>` : ''}</div>
      ${g ? `<p class="pa">${g.map(esc).join(' &middot; ')}</p>`
          : (m[1] ? '<p class="pa">grammar code not in the table</p>' : '')}
      <div id="lx${mi}"></div></div>`);
  });
  o.push('</div>');
  sheet(o.join(''));

  for (let mi = 0; mi < parts.length; mi++) {
    const m = parts[mi], simple = m[2] || m[0];
    const el = document.getElementById('lx' + mi);
    if (!el) continue;
    const [e, cc] = await Promise.all([lex(m[0]).then(x => x || lex(simple)), conc(simple)]);
    const bits = [];
    if (e === OFFLINE) {
      bits.push(`<p class="pa">The dictionary entry for this word has not been
        downloaded yet, and there is no connection to fetch it. The parsing
        above is already on your phone. Open this word once with a signal and
        it will be here from then on.</p>`);
      el.innerHTML = bits.join('');
      continue;
    }
    if (e) {
      bits.push(`<p class="de"><b>${esc(e[2] || '')}</b></p>`);
      if (e[0]) bits.push(`<p class="pa">${esc(e[0])} &middot; <i>${esc(e[1] || '')}</i></p>`);
      if (e[3]) {
        const full = String(e[3]);
        const short = full.length > 240;
        bits.push(`<p class="de" id="def${mi}">${esc(short ? full.slice(0, 240) + '…' : full)}</p>`);
        if (short) bits.push(`<button class="more" data-expand="${mi}"
          data-full="${esc(full)}">Read the whole entry →</button>`);
      }
    } else bits.push('<p class="pa">No lexicon entry under this number.</p>');
    if (cc && cc !== OFFLINE) bits.push(`<button class="more" data-conc="${esc(simple)}">
      Concordance: ${cc[0].toLocaleString()} verse${cc[0] === 1 ? '' : 's'} →</button>`);
    bits.push(`<button class="more" data-dict="${esc((e && e[2]) || t[3] || '')}">
      Look up in the Bible dictionary →</button>`);
    el.innerHTML = bits.join('');
  }
}

/* -------------------------------------------------------- concordance */
async function concSheet(strongs) {
  const [cc, e] = await Promise.all([conc(strongs), lex(strongs)]);
  if (cc === OFFLINE) return sheet(`<p class="lbl">Concordance</p>
    <p class="de">This part of the concordance has not been downloaded yet, and
    there is no connection to fetch it. Try again with a signal.</p>`);
  if (!cc) return sheet('<p class="load">Nothing indexed under that number.</p>');
  const shown = cc[1].length;
  const o = [`<p class="lbl">Concordance &middot; ${esc(strongs)}</p>`];
  if (e) o.push(`<div class="hw"><span class="big ${strongs[0] === 'H' ? 'heb' : 'grk'}">${esc(e[0])}</span>
    <span class="tr">${esc(e[1] || '')}</span></div><p class="de"><b>${esc(e[2] || '')}</b></p>`);
  o.push(`<p class="oc">${cc[0].toLocaleString()} verses contain this word${
    shown < cc[0] ? ` &middot; showing the first ${shown.toLocaleString()}` : ''}</p>`);
  o.push('<div style="margin-top:12px">');
  cc[1].forEach(vk => o.push(
    `<button class="hit" data-ref="${esc(vk)}"><span class="r">${esc(refLabel(vk))}</span></button>`));
  o.push('</div>');
  sheet(o.join(''));
}

/* --------------------------------------------------------- dictionary */
async function dictSheet(term) {
  await lazy.dictIx();
  const key = String(term || '').trim().toLowerCase().replace(/[^a-z' ]/g, '');
  let hits = S.dictIx[key];
  if (!hits) {
    const first = key.split(' ')[0];
    hits = S.dictIx[first] || null;
    if (!hits) {
      const near = Object.keys(S.dictIx)
        .filter(k => first.length > 2 && k.startsWith(first.slice(0, Math.max(3, first.length - 1))))
        .slice(0, 25);
      if (!near.length) return sheet(
        `<p class="lbl">Bible dictionary</p><p class="de">No entry for
         “${esc(term)}”. The dictionary covers names, places and
         topics rather than every English word.</p>`);
      return sheet(`<p class="lbl">Bible dictionary</p>
        <p class="de">Nothing filed under “${esc(term)}”. Did you mean:</p>
        <div style="margin-top:10px">${near.map(k =>
          `<button class="hit" data-dict="${esc(k)}"><span class="r">${esc(k)}</span></button>`
        ).join('')}</div>`);
    }
  }
  const o = [`<p class="lbl">Bible dictionary</p>`];
  for (const [eid, b, label] of hits.slice(0, 8)) {
    let sh;
    try { sh = await get(`dict/${b}.json`); } catch { continue; }
    const e = sh[eid];
    if (!e) continue;
    o.push(`<div class="mo"><div class="hw"><span style="font-size:1.15rem;font-weight:600">${esc(label)}</span>
      ${e.num > 1 ? `<span class="ot">sense ${e.num}</span>` : ''}</div>
      <p class="de" style="white-space:pre-wrap">${esc(e.body || '')}</p>
      <p class="oc">${esc(e.src || 'Easton’s Bible Dictionary')}</p></div>`);
  }
  sheet(o.join('') || '<p class="load">Entry body missing.</p>');
}

/* ------------------------------------------------- place / person / event */
async function placeSheet(vi, i) {
  const p = (CH.v[vi].p || [])[i]; if (!p) return;
  await Promise.all([lazy.place(), lazy.pix().catch(() => {}),
                     lazy.pano().catch(() => { S.pano = {}; })]);
  const d = (S.place || {})[p[0]] || {};
  const lat = d.lat != null ? d.lat : p[2], lon = d.lon != null ? d.lon : p[3];
  const STAT = {
    identified: ['Identified', 'The modern site is agreed on by the people who study this.'],
    disputed:   ['Disputed', 'Scholars propose more than one modern site. The coordinates are one candidate, not a settled answer.'],
    region:     ['Region', 'A district or territory rather than a single spot. The coordinates are a centre point.'],
    unknown:    ['Not located', 'Named in the text, but nobody knows where it was.']
  };
  const st = STAT[d.status || p[1]] || STAT.unknown;
  const o = [`<p class="lbl">Place &middot; ${esc(refLabel(CH.b + '.' + CH.c + '.' + CH.v[vi].n))}</p>`];
  o.push(`<div class="hw"><span style="font-size:1.4rem;font-weight:600">${esc(p[0])}</span></div>`);
  const pic = (S.pix || {})[p[0]];
  if (pic) {
    // Attribution is a licence condition for most of these, not a courtesy,
    // so the credit travels with the picture rather than being tucked away.
    const credit = [pic.artist, pic.licence].filter(Boolean).join(' \u00b7 ');
    o.push(`<figure style="margin:0 0 14px">
      <img src="data/pix/${esc(pic.file)}" alt="Photograph of ${esc(p[0])}"
        width="${pic.w}" height="${pic.h}" loading="lazy" decoding="async"
        style="width:100%;height:auto;border-radius:10px;display:block;
               background:var(--line-soft)">
      <figcaption class="oc" style="margin-top:6px">${
        (d.status || p[1]) === 'disputed'
          ? 'A photograph of <b>one</b> of the proposed sites. '
          : ''}${credit ? esc(credit) : 'Wikimedia Commons'}${
        pic.page ? ` \u00b7 <a href="${esc(pic.page)}" target="_blank" rel="noopener">source</a>` : ''
      }</figcaption></figure>`);
  }
  if (d.modern) o.push(`<p class="de">Today: <b>${esc(d.modern)}</b></p>`);
  o.push(`<p class="pa"><b>${esc(st[0])}.</b> ${esc(st[1])}</p>`);
  if (d.types) o.push(`<p class="pa">Type: ${esc(String(d.types).replace(/[,;]+/g, ', '))}</p>`);
  if (d.desc) o.push(`<p class="de">${esc(d.desc)}</p>`);
  if (lat && lon) {
    o.push(`<p class="oc">${(+lat).toFixed(4)}\u00b0, ${(+lon).toFixed(4)}\u00b0</p>`);
    // OpenBible's score saturates at 500 for an undisputed site, so the
    // number only says something when the identification is contested.
    const st2 = d.status || p[1];
    if (st2 === 'disputed' && d.conf != null) {
      o.push(`<p class="pa">${d.conf < 0
        ? 'The sources that weighed in lean <b>against</b> this location'
        : `Weight of opinion for this site: <b>${d.conf}</b>`}${
        d.votes > 1 ? `, out of ${d.votes} proposals considered` : ''}. The rival
        sites carry the rest of the vote.</p>`);
    } else if (st2 === 'identified') {
      o.push('<p class="pa">The sources are unanimous on this one.</p>');
    }
    // Three ways to look at it: the plain map, the ground from above, and
    // street level wherever anyone has driven a camera down that road.
    o.push(`<p class="lbl" style="margin:16px 0 6px">Go and look</p>
      <div class="opts">
      <a class="opt" target="_blank" rel="noopener"
        href="https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=10/${lat}/${lon}">Map ↗</a>
      <a class="opt" target="_blank" rel="noopener"
        href="https://www.google.com/maps/@${lat},${lon},2500m/data=!3m1!1e3">From above ↗</a>
      <a class="opt" target="_blank" rel="noopener"
        href="https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=${lat},${lon}">Stand there and look around ↗</a>
      </div>
      <p class="pa">Street level only exists where somebody has driven a camera
      down that road, which for a good many of these is nowhere. All three open
      in another app and need a connection.</p>`);
    // Stay here and look around instead, where somebody has left a
    // photosphere. Loaded only if asked for.
    const pano = (S.pano || {})[p[0]];
    if (pano) {
      o.push(`<button class="opt" data-look="${esc(p[0])}"
        style="margin-top:10px">◌ Stand here and look around, without
        leaving this page</button>`);
      o.push('<div id="panoHost"></div>');
    }
  } else o.push('<p class="oc">No coordinates — the site is unlocated.</p>');
  if (d.n) {
    o.push(`<p class="lbl" style="margin:18px 0 6px">Named in ${d.n} verse${d.n === 1 ? '' : 's'}</p>`);
    (d.refs || []).slice(0, 120).forEach(vk => o.push(
      `<button class="hit" data-ref="${esc(vk)}"><span class="r">${esc(refLabel(vk))}</span></button>`));
  }
  o.push(`<button class="more" data-dict="${esc(p[0])}">Dictionary entry for ${esc(p[0])} →</button>`);
  sheet(o.join(''));
}

async function personSheet(vi, i) {
  const name = (CH.v[vi].pe || [])[i]; if (!name) return;
  await lazy.person();
  const d = (S.person || {})[name] || {};
  const senses = [d, ...(d.also || [])].filter(x => x && (x.n || x.title));
  const o = [`<p class="lbl">Person &middot; ${esc(refLabel(CH.b + '.' + CH.c + '.' + CH.v[vi].n))}</p>`];
  o.push(`<div class="hw"><span style="font-size:1.4rem;font-weight:600">${esc(name)}</span></div>`);
  if (senses.length > 1) o.push(`<p class="pa">${senses.length} different people in the
    text carry this name. They are listed separately below.</p>`);
  senses.forEach((s, si) => {
    o.push('<div class="mo">');
    if (senses.length > 1) o.push(`<p class="lbl">#${si + 1}</p>`);
    if (s.title) o.push(`<p class="de">${esc(s.title)}</p>`);
    const bio = [];
    if (s.sex) bio.push(esc(s.sex));
    if (s.born != null) bio.push('born ' + esc(s.born));
    if (s.died != null) bio.push('died ' + esc(s.died));
    if (bio.length) o.push(`<p class="oc">${bio.join(' &middot; ')}</p>`);
    if (s.n) {
      o.push(`<p class="oc">named in ${s.n} verse${s.n === 1 ? '' : 's'}</p>`);
      (s.refs || []).slice(0, 80).forEach(vk => o.push(
        `<button class="hit" data-ref="${esc(vk)}"><span class="r">${esc(refLabel(vk))}</span></button>`));
    }
    o.push('</div>');
  });
  o.push(`<button class="more" data-dict="${esc(name)}">Dictionary entry for ${esc(name)} →</button>`);
  sheet(o.join(''));
}

function yearLabel(y) {
  if (y == null) return null;
  return y < 0 ? Math.abs(y) + ' BC' : y + ' AD';
}
async function eventSheet(vi, i) {
  const ev = (CH.v[vi].ev || [])[i]; if (!ev) return;
  await lazy.event();
  const d = (S.event || {})[String(ev[0])] || {};
  const o = [`<p class="lbl">Event &middot; ${esc(refLabel(CH.b + '.' + CH.c + '.' + CH.v[vi].n))}</p>`];
  o.push(`<div class="hw"><span style="font-size:1.3rem;font-weight:600">${esc(ev[1])}</span></div>`);
  if (d.dur) o.push(`<p class="pa">lasted about ${esc(d.dur)}</p>`);
  o.push(`<p class="lbl" style="margin:18px 0 4px">When it happened, by scheme</p>`);
  o.push(`<p class="pa" style="margin:0 0 8px">The schemes disagree. That is not a
    bug in this app — it is the actual state of the field.</p>`);
  (S.chron.schemes || []).forEach(s => {
    const dt = (d.dates || {})[s.scheme_id];
    const y = dt ? yearLabel(dt[0]) : null;
    const end = dt && dt[1] != null && dt[1] !== dt[0] ? yearLabel(dt[1]) : null;
    o.push(`<div class="row${s.scheme_id === S.chrono ? ' sel' : ''}">
      <span>${esc(s.name)}</span>
      <span class="y${y ? '' : ' none'}">${y ? esc(y + (end ? ' – ' + end : '')) : 'no date in this scheme'}</span></div>`);
  });
  if ((d.refs || []).length) {
    o.push(`<p class="lbl" style="margin:18px 0 6px">Passages</p>`);
    d.refs.slice(0, 150).forEach(vk => o.push(
      `<button class="hit" data-ref="${esc(vk)}"><span class="r">${esc(refLabel(vk))}</span></button>`));
  }
  o.push(`<button class="more" data-go="chrono">See it on the timeline →</button>`);
  sheet(o.join(''));
}

/* --------------------------------------------------- notes / commentary */
function noteSheet(vi) {
  const v = CH.v[vi], ns = v.nt || [];
  const o = [`<p class="lbl">Notes on ${esc(refLabel(CH.b + '.' + CH.c + '.' + v.n))}</p>`];
  o.push(`<p class="pa" style="margin:0 0 14px">Verse-by-verse notes on wording,
    idiom, grammar and cultural background, written for translators — which
    makes them unusually plain about what the original actually says.</p>`);
  ns.forEach(n => {
    o.push('<div class="note-b">');
    if (n[0]) o.push(`<p class="note-q" style="margin:0 0 4px">${esc(n[0])}</p>`);
    o.push(md(n[2] || ''));
    if (n[1]) o.push(`<p class="oc" style="margin-top:6px">${esc(n[1])}</p>`);
    o.push('</div>');
  });
  o.push(`<p class="oc">unfoldingWord Translation Notes, CC BY-SA 4.0</p>`);
  sheet(o.join(''));
}
function md(t) {
  return esc(t)
    .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')
    .replace(/\[([^\]]+)\]/g, '<i>$1</i>')
    .replace(/\n/g, '<br>');
}

function xrefSheet(vi) {
  const v = CH.v[vi], xs = v.xr || [];
  const top = xs[0] ? xs[0][1] : 1;
  const o = [`<p class="lbl">Cross-references from ${esc(refLabel(CH.b + '.' + CH.c + '.' + v.n))}</p>`];
  o.push(`<p class="pa" style="margin:0 0 14px">Ranked by how strongly readers and
    editors have linked the two passages. The bar is relative weight, not certainty.</p>`);
  xs.forEach(x => {
    const pct = Math.max(6, Math.round(100 * x[1] / (top || 1)));
    o.push(`<button class="hit" data-ref="${esc(x[0])}">
      <span class="r">${esc(refLabel(x[0]))}</span>
      <span style="display:block;height:3px;margin-top:6px;border-radius:2px;
        background:var(--accent);width:${pct}%;opacity:.55"></span></button>`);
  });
  o.push(`<p class="oc" style="margin-top:12px">Treasury of Scripture Knowledge and
    related sets, aggregated by OpenBible.info</p>`);
  sheet(o.join(''));
}

/* ============================================================ readability */
/* Written for people who will be reading this at seventy. The default is
   larger than a designer's instinct, and the range goes further than feels
   necessary, because the person who needs 28px is exactly the person least
   likely to go hunting for a setting. */
const FS_MIN = 17, FS_MAX = 30, FS_STEP = 1;

const SCHEME_ORDER = ['paper', 'sepia', 'contrast', 'dim', 'night', 'black', 'auto'];

function applyDisplay() {
  const r = document.documentElement;
  r.style.setProperty('--fs', S.fs + 'px');
  r.setAttribute('data-scheme', S.scheme);
  const m = document.querySelector('meta[name=theme-color]:not([media])');
  if (m) m.setAttribute('content',
    getComputedStyle(r).getPropertyValue('--paper').trim() || '#FCFBF8');
}

function displaySheet() {
  sheet(`<p class="lbl">Reading</p>` + displayPanel() +
    `<div class="mo" style="margin-top:20px">
      <p style="font-weight:600;margin:0 0 6px">Or have it read to you</p>
      <p class="de" style="margin:0">Every chapter has a spoken reading behind the
      <b>Listen</b> button at the top and bottom of the text. They are public-domain
      recordings streamed from archive.org, so they need a connection \u2014 the text
      itself does not.</p></div>` +
    `<button class="more" data-go="offline">Keep it offline \u2014 download the whole Bible \u2192</button>`);
}

function displayPanel() {
  const pct = Math.round(100 * S.fs / 19);
  return `
  <p class="lbl" style="margin-top:4px">Text size</p>
  <div style="display:flex;gap:10px;align-items:stretch;margin:6px 0 10px">
    <button class="szbtn" data-fs="-1" aria-label="Smaller text"
      ${S.fs <= FS_MIN ? 'disabled' : ''}>A<span style="font-size:.7em">−</span></button>
    <div style="flex:1;display:flex;flex-direction:column;align-items:center;
                justify-content:center;border:1px solid var(--line);
                border-radius:10px;padding:6px">
      <span style="font-size:var(--t4);font-weight:600">${S.fs}px</span>
      <span class="ot">${pct}%</span>
    </div>
    <button class="szbtn" data-fs="1" aria-label="Larger text"
      ${S.fs >= FS_MAX ? 'disabled' : ''}>A<span style="font-size:.7em">+</span></button>
  </div>
  <p class="de" style="border:1px solid var(--line);border-radius:10px;
     padding:12px;margin:0 0 6px">For God so loved the world, that he gave his
     only begotten Son.</p>
  <p class="ot" style="margin:0 0 18px">That is how a verse will look.</p>

  <p class="lbl">Pictures</p>
  <button class="opt ${S.showPix ? 'on' : ''}" data-setpix="1" style="margin-bottom:6px">${
    S.showPix ? '\u2713 Showing the engravings in the text'
              : 'Engravings hidden \u2014 words only'}</button>
  <p class="pa" style="margin:0 0 6px">Gustave Dor\u00e9 engraved these in 1866.
    They are one Victorian artist's reading of the scene, not a photograph
    and not evidence \u2014 but he was very good, and they sit where the text
    puts them.</p>
  <button class="more" data-go="plates" style="margin:0 0 18px">See all 150
    engravings \u2192</button>

  <p class="lbl">Colour</p>
  <div class="swatches">
    ${SCHEME_ORDER.map(k => {
      const sc = (S.schemes || {})[k];
      const on = S.scheme === k;
      if (k === 'auto') {
        return `<button class="sw ${on ? 'on' : ''}" data-setscheme3="auto"
          aria-label="Match my phone">
          <span class="sw-chip" style="background:linear-gradient(135deg,#FCFBF8 50%,#15181C 50%)">
            <span style="color:#141210;font-weight:600">A</span></span>
          <span class="sw-name">${on ? '\u2713 ' : ''}Match my phone</span></button>`;
      }
      if (!sc) return '';
      return `<button class="sw ${on ? 'on' : ''}" data-setscheme3="${esc(k)}"
        aria-label="${esc(sc.name)}">
        <span class="sw-chip" style="background:${esc(sc.paper)};border-color:${esc(sc.ink)}33">
          <span style="color:${esc(sc.ink)};font-weight:600">A</span></span>
        <span class="sw-name">${on ? '\u2713 ' : ''}${esc(sc.name)}</span></button>`;
    }).join('')}
  </div>
  <p class="pa" style="margin:8px 0 18px">${
    esc(((S.schemes || {})[S.scheme] || {}).note ||
        'Follows whatever your phone is set to.')}</p>
  <p class="pa" style="margin:0 0 18px">Dark print on a light page tested
    better for most readers over sixty, which is why Paper is the default.
    But readers with a cataract often do better on a dark screen, because it
    throws off less light to scatter. Try them. Your own eyes are the evidence
    here, not ours.</p>`;
}

/* =========================================================== offline save */
/* Caching only what somebody happens to open is no use to a person about to
   lose signal for a week. This pulls the lot down while there is wifi. The
   service worker caches anything fetched from data/, so downloading here is
   simply fetching it - no second code path to keep in step. */
let DL = null;        // { stop, done, total, failed }

const MB = b => (b / 1048576).toFixed(b >= 104857600 ? 0 : 1) + ' MB';

async function offlineView() {
  let man;
  try { man = S.man || (S.man = await get('offline_manifest.json')); }
  catch { $('#view').innerHTML = '<p class="load">Could not load the file list.</p>'; return; }

  let est = null, persisted = false;
  try { est = await navigator.storage.estimate(); } catch { /* not offered */ }
  try { persisted = await navigator.storage.persisted(); } catch { /* ditto */ }

  const o = [];
  o.push('<h1 style="font-size:1.3rem;margin:6px 0 2px">Keep it offline</h1>');
  o.push(`<p class="ot" style="margin:0 0 14px">Download it now, read it
    anywhere — no signal, no data, no account.</p>`);
  o.push(`<p class="de">Chapters you open are already kept. This takes the rest,
    so nothing is missing when the signal goes. Best done on wifi.</p>`);
  o.push(`<p class="pa" style="margin:10px 0 0">One thing cannot be kept: the
    spoken readings. They are 2.5&nbsp;GB of recordings held by archive.org and
    they stream from there, so <b>Listen</b> needs a connection even after you
    have downloaded everything below. Every word of the text, and every
    picture, works with no signal at all.</p>`);

  const keys = Object.keys(man.tiers);
  o.push('<div style="margin-top:18px">');
  keys.forEach(k => {
    const t = man.tiers[k];
    const on = S.dlTiers[k] !== false;
    o.push(`<button data-tier="${esc(k)}" style="display:block;width:100%;
      text-align:left;border:1px solid ${on ? 'var(--accent)' : 'var(--line)'};
      border-radius:10px;padding:14px;margin:0 0 10px;color:inherit;
      background:${on ? 'var(--accent-soft)' : 'var(--surface)'}">
      <span style="display:flex;justify-content:space-between;gap:10px;align-items:baseline">
        <span style="font-weight:600">${on ? '✓ ' : ''}${esc(t.label)}</span>
        <span class="ot">${esc(MB(t.bytes))}</span></span>
      <span class="de" style="display:block;margin-top:6px;color:var(--ink-soft)">${esc(t.note)}</span>
    </button>`);
  });
  o.push('</div>');

  const chosen = keys.filter(k => S.dlTiers[k] !== false);
  const bytes = chosen.reduce((n, k) => n + man.tiers[k].bytes, 0);
  const files = chosen.reduce((n, k) => n + man.tiers[k].count, 0);

  if (DL) {
    const pct = DL.total ? Math.round(100 * DL.done / DL.total) : 0;
    o.push(`<div class="mo"><p style="font-weight:600;margin:0 0 8px">Downloading — ${pct}%</p>
      <div style="height:6px;border-radius:3px;background:var(--line);overflow:hidden">
        <div style="height:100%;width:${pct}%;background:var(--accent)"></div></div>
      <p class="oc" style="margin-top:8px">${DL.done.toLocaleString()} of
        ${DL.total.toLocaleString()} files${DL.failed ? ` · ${DL.failed} could not be fetched` : ''}</p>
      <button class="more" data-dlstop="1">Stop</button></div>`);
  } else {
    o.push(`<button class="chip" data-dlstart="1" style="min-height:48px;
      padding:12px 18px;border-color:var(--accent);color:var(--accent);
      font-size:.95rem;margin-top:4px">
      Download ${esc(MB(bytes))} · ${files.toLocaleString()} files</button>`);
    if (!chosen.length) o.push('<p class="pa">Nothing selected.</p>');
  }

  if (est && est.usage != null) {
    o.push(`<p class="lbl" style="margin:22px 0 6px">Already on this phone</p>`);
    o.push(`<p class="de">${esc(MB(est.usage))} stored${
      est.quota ? ` of roughly ${esc(MB(est.quota))} this browser allows` : ''}.</p>`);
  }
  o.push(`<p class="pa">${persisted
    ? 'The browser has agreed to keep this and not clear it to make room.'
    : 'A browser may clear downloads when it runs short of space. Adding this page to your home screen makes that much less likely.'}</p>`);
  o.push(`<button class="more" data-dlclear="1">Delete the downloads</button>`);
  o.push(footer());
  $('#view').innerHTML = o.join('');
  window.scrollTo(0, 0);
}

async function startDownload() {
  const man = S.man;
  if (!man || DL) return;
  try { await navigator.storage.persist(); } catch { /* best effort */ }
  const urls = [];
  Object.keys(man.tiers).forEach(k => {
    if (S.dlTiers[k] === false) return;
    man.tiers[k].files.forEach(f => urls.push(f[0]));
  });
  DL = { stop: false, done: 0, total: urls.length, failed: 0 };
  await offlineView();

  let i = 0, painted = 0;
  const worker = async () => {
    while (!DL.stop) {
      const n = i++;
      if (n >= urls.length) return;
      try {
        const r = await fetch(urls[n], { cache: 'no-store' });
        if (!r.ok) throw new Error(String(r.status));
        await r.arrayBuffer();           // drain it so the worker stores it
      } catch (e) { DL.failed++; }
      DL.done++;
      // repaint now and then, not 3,476 times
      if (DL.done - painted > 25 || DL.done === DL.total) {
        painted = DL.done;
        if (location.hash.indexOf('offline') >= 0) offlineView();
      }
    }
  };
  await Promise.all([worker(), worker(), worker(), worker(), worker(), worker()]);

  const failed = DL.failed, stopped = DL.stop, done = DL.done;
  DL = null;
  if (location.hash.indexOf('offline') >= 0) {
    await offlineView();
    const msg = stopped
      ? `Stopped after ${done.toLocaleString()} files. What came down is kept — start again any time and it picks up the rest.`
      : failed
        ? `Finished, but ${failed.toLocaleString()} file${failed === 1 ? '' : 's'} could not be fetched. Run it again on a better connection.`
        : 'Done. The whole thing is on this phone now.';
    $('#view').insertAdjacentHTML('afterbegin',
      `<p class="de" style="border:1px solid var(--good);color:var(--good);
        border-radius:10px;padding:12px;margin:0 0 14px">${esc(msg)}</p>`);
  }
}

async function clearDownloads() {
  try {
    const ks = await caches.keys();
    await Promise.all(ks.filter(k => k.indexOf('data') >= 0).map(k => caches.delete(k)));
  } catch (e) { /* nothing to clear */ }
  offlineView();
}

/* ============================================================= commentary */
let CMF = 'all';                       // source filter inside the sheet

async function commentary(book, ch) {
  return get(`cm/${book}.${ch}.json`);
}
function cmRender(units, title, note) {
  const meta = (S.cmMeta || {}).sources || {};
  const order = (S.cmMeta || {}).order || [];
  const present = order.filter(sid => units.some(u => u[0] === sid));
  const shown = CMF === 'all' ? units : units.filter(u => u[0] === CMF);
  const o = [`<p class="lbl">${esc(title)}</p>`];
  if (note) o.push(`<p class="pa" style="margin:0 0 12px">${esc(note)}</p>`);
  if (present.length > 1) {
    o.push(`<div class="tabs"><button data-cmf="all" class="${CMF === 'all' ? 'on' : ''}">All ${units.length}</button>`);
    present.forEach(sid => {
      const n = units.filter(u => u[0] === sid).length;
      o.push(`<button data-cmf="${esc(sid)}" class="${CMF === sid ? 'on' : ''}">${
        esc((meta[sid] || [sid])[0])} ${n}</button>`);
    });
    o.push('</div>');
  }
  if (!shown.length) o.push('<p class="pa">Nothing from that commentator here.</p>');
  shown.forEach(u => {
    const [sid, kind, utitle, v1, v2, paras] = u;
    const m = meta[sid] || [sid, ''];
    o.push('<div class="mo">');
    o.push(`<p style="font-weight:600;margin:0 0 2px">${esc(m[0])}</p>`);
    o.push(`<p class="oc" style="margin:0 0 8px">${esc(m[1])}${
      kind === 'book' ? ' \u00b7 preface to the book'
      : v1 == null ? ' \u00b7 on the whole chapter'
      : ` \u00b7 on ${v1 === v2 ? 'verse ' + v1 : 'verses ' + v1 + '\u2013' + v2}`}</p>`);
    if (utitle) o.push(`<p class="de" style="font-style:italic;margin:0 0 8px">${esc(utitle)}</p>`);
    paras.forEach(t => o.push(`<p class="de" style="margin:0 0 10px">${esc(t)}</p>`));
    o.push('</div>');
  });
  o.push(`<p class="oc" style="margin-top:14px">All six are in the public domain.
    Nothing under copyright was included.</p>`);
  return o.join('');
}

async function cmSheet(vi) {
  await lazy.cmMeta();
  const v = CH.v[vi];
  sheet('<p class="load">Loading the commentators\u2026</p>');
  let d;
  try { d = await commentary(CH.b, CH.c); }
  catch { return sheet('<p class="load">Commentary would not load.</p>'); }
  const units = d.u.filter(u => u[3] != null && v.n >= u[3] && v.n <= (u[4] || u[3]));
  CMV = vi;
  sheet(cmRender(units,
    'Commentary on ' + refLabel(CH.b + '.' + CH.c + '.' + v.n),
    'Six commentators, written between 1599 and 1885. They disagree with each ' +
    'other, and with you. That is what they are for.'));
}
async function cmChapterSheet() {
  await lazy.cmMeta();
  sheet('<p class="load">Loading the commentators\u2026</p>');
  let d;
  try { d = await commentary(CH.b, CH.c); }
  catch { return sheet('<p class="load">Commentary would not load.</p>'); }
  const units = d.u.filter(u => u[3] == null);
  CMV = null;
  sheet(cmRender(units,
    'On ' + refLabel(CH.b + '.' + CH.c) + ' as a whole',
    'Prefaces to the book and overviews of the chapter, before the ' +
    'verse-by-verse notes.'));
}
let CMV = null;

/* ============================================================== searching */
let SQ = '', STAB = 'verse';
const tokens = q => (q || '').toLowerCase().split(/[^a-z']+/)
  .map(t => t.replace(/^'+|'+$/g, '')).filter(t => t.length > 1);

async function runSearch(q, tab) {
  SQ = q; STAB = tab || STAB;
  const o = [];
  o.push(`<h1 style="font-size:1.3rem;margin:6px 0 12px">Search</h1>`);
  o.push(`<input type="search" id="q" value="${esc(q)}" enterkeyhint="search"
    placeholder="a word, a phrase, or John 3:16" autocomplete="off"
    autocorrect="off" autocapitalize="none" spellcheck="false">`);
  o.push(`<div class="tabs" style="margin-top:12px">${
    [['verse', 'Verses'], ['word', 'Original words'], ['dict', 'Dictionary'], ['note', 'Notes']]
      .map(([k, l]) => `<button data-tab="${k}" class="${STAB === k ? 'on' : ''}">${l}</button>`).join('')
  }</div>`);
  o.push('<div id="results"></div>');
  o.push(footer());
  $('#view').innerHTML = o.join('');
  const r = parseRef(q);
  if (r) $('#results').insertAdjacentHTML('afterbegin',
    `<button class="hit" data-ref="${esc(r.book + '.' + r.ch + (r.v ? '.' + r.v : ''))}"
      style="border:1px solid var(--accent);border-radius:10px;padding:12px;margin-bottom:14px">
      <span class="r">Go to ${esc(refLabel(r.book + '.' + r.ch + (r.v ? '.' + r.v : '')))}</span>
      <span class="t">That looks like a reference.</span></button>`);
  const ts = tokens(q);
  if (!ts.length) return;
  const box = $('#results');
  box.insertAdjacentHTML('beforeend', '<p class="load">Searching…</p>');
  try {
    if (STAB === 'verse') await searchRefs('w', ts, box, 'in the King James text');
    else if (STAB === 'note') await searchRefs('n', ts, box, 'in the translation notes');
    else if (STAB === 'word') await searchWords(ts, box);
    else await searchDict(ts, box);
  } catch (e) {
    box.innerHTML = `<p class="load">Search failed: ${esc(e.message)}</p>`;
  }
}

async function searchRefs(kind, ts, box, where) {
  const lists = await Promise.all(ts.map(t => idx(kind, t)));
  const missing = ts.filter((t, i) => !lists[i]);
  const found = lists.filter(Boolean);
  if (!found.length) {
    box.querySelector('.load').outerHTML =
      `<p class="load">No match ${esc(where)} for ${esc(ts.join(', '))}.</p>`;
    return;
  }
  let set = new Set(found[0][1]);
  for (let i = 1; i < found.length; i++) {
    const s = new Set(found[i][1]);
    set = new Set([...set].filter(x => s.has(x)));
  }
  const refs = [...set].sort(byRef);
  const capped = found.some(f => f[1].length < f[0]);
  const o = [];
  o.push(`<p class="oc">${refs.length.toLocaleString()} verse${refs.length === 1 ? '' : 's'}
    ${ts.length > 1 ? 'contain all of these words ' : ''}${esc(where)}${
    capped ? ' &middot; very common words are capped, so a rare word gives better results' : ''}</p>`);
  if (missing.length) o.push(`<p class="oc">not indexed: ${esc(missing.join(', '))}</p>`);
  o.push('<div id="hits" style="margin-top:10px">');
  refs.slice(0, 300).forEach(vk => o.push(
    `<button class="hit" data-ref="${esc(vk)}"><span class="r">${esc(refLabel(vk))}</span>
     <span class="t" data-snip="${esc(vk)}"></span></button>`));
  o.push('</div>');
  if (refs.length > 300) o.push(`<p class="oc">showing the first 300</p>`);
  box.querySelector('.load').outerHTML = o.join('');
  snippets(refs.slice(0, 14), ts);
}
function byRef(a, b) {
  const pa = a.split('.'), pb = b.split('.');
  const ia = S.bookIx[pa[0]], ib = S.bookIx[pb[0]];
  return (ia ? ia.n : 999) - (ib ? ib.n : 999) || (+pa[1] - +pb[1]) || (+pa[2] - +pb[2]);
}
async function snippets(refs, ts) {
  const byCh = {};
  refs.forEach(vk => {
    const p = vk.split('.'), k = p[0] + '.' + p[1];
    if (!byCh[k]) byCh[k] = [];
    byCh[k].push(vk);
  });
  for (const key in byCh) {
    let d; try { d = await get(`ch/${key}.json`); } catch { continue; }
    byCh[key].forEach(vk => {
      const n = +vk.split('.')[2];
      const v = d.v.find(x => x.n === n); if (!v) return;
      let txt = (v.x || {})[S.tx] || (v.x || {}).KJV || '';
      const el = document.querySelector(`[data-snip="${vk}"]`); if (!el) return;
      let html = esc(txt);
      ts.forEach(t => { html = html.replace(new RegExp(`\\b(${t})`, 'gi'), '<b>$1</b>'); });
      el.innerHTML = html;
    });
  }
}

async function searchWords(ts, box) {
  const lists = await Promise.all(ts.map(t => idx('g', t)));
  const hits = [];
  lists.forEach(l => (l || []).forEach(([s, n]) => hits.push([s, n])));
  if (!hits.length) {
    box.querySelector('.load').outerHTML =
      `<p class="load">No original-language word is glossed with ${esc(ts.join(', '))}.</p>`;
    return;
  }
  hits.sort((a, b) => b[1] - a[1]);
  const o = [`<p class="oc">Original-language words translated with
    “${esc(ts.join(' '))}”, commonest first</p><div style="margin-top:10px">`];
  const top = hits.slice(0, 40);
  const ents = (await Promise.all(top.map(h => lex(h[0]))))
    .map(x => x === OFFLINE ? null : x);
  top.forEach(([s, n], i) => {
    const e = ents[i];
    o.push(`<button class="hit" data-conc="${esc(s)}">
      <span class="r">${esc(s)}</span>
      <span class="t">${e ? `<span class="${s[0] === 'H' ? 'heb' : 'grk'}"
        style="font-size:1.1rem">${esc(e[0])}</span> <i>${esc(e[1] || '')}</i> — ${esc(e[2] || '')}` : ''}
        <span class="ot"> &middot; ${n} time${n === 1 ? '' : 's'}</span></span></button>`);
  });
  o.push('</div>');
  box.querySelector('.load').outerHTML = o.join('');
}

async function searchDict(ts, box) {
  await lazy.dictIx();
  const q = ts.join(' ');
  const keys = Object.keys(S.dictIx);
  const exact = keys.filter(k => k === q);
  const pre = keys.filter(k => k !== q && k.startsWith(q)).sort();
  const sub = keys.filter(k => !k.startsWith(q) && k.includes(q)).sort();
  const all = [...exact, ...pre, ...sub].slice(0, 120);
  if (!all.length) {
    box.querySelector('.load').outerHTML =
      `<p class="load">No dictionary headword contains “${esc(q)}”.</p>`;
    return;
  }
  const o = [`<p class="oc">${all.length} dictionary headword${all.length === 1 ? '' : 's'}</p>
    <div style="margin-top:10px">`];
  all.forEach(k => {
    const label = (S.dictIx[k][0] || [])[2] || k;
    o.push(`<button class="hit" data-dict="${esc(k)}"><span class="r">${esc(label)}</span>
      ${S.dictIx[k].length > 1 ? `<span class="t">${S.dictIx[k].length} senses</span>` : ''}</button>`);
  });
  o.push('</div>');
  box.querySelector('.load').outerHTML = o.join('');
}





/* ========================================================= looking around */
/* A photosphere is an equirectangular image: longitude left to right,
   latitude top to bottom, twice as wide as it is tall. Looking around
   inside one means putting a camera at the centre of a sphere, which means
   WebGL - written out here rather than pulled from a content network,
   because a Bible that has to work with no signal cannot depend on a
   script from somebody else's server.

   One full-screen triangle pair, one shader that turns each pixel back
   into a direction and reads the image along it, one texture. The images
   are 2048x1024 exactly, which is a power of two in both directions, so
   the horizontal wrap is the hardware's REPEAT and costs nothing. */

const VSRC = `
attribute vec2 a;
varying vec2 v;
void main() { v = a; gl_Position = vec4(a, 0.0, 1.0); }`;

const FSRC = `
precision highp float;
varying vec2 v;
uniform sampler2D tex;
uniform float yaw, pitch, fov, aspect;
const float PI = 3.141592653589793;
void main() {
  float t = tan(fov * 0.5);
  vec3 d = normalize(vec3(v.x * t * aspect, v.y * t, -1.0));
  float cp = cos(pitch), sp = sin(pitch);
  d = vec3(d.x, d.y * cp - d.z * sp, d.y * sp + d.z * cp);
  float cy = cos(yaw), sy = sin(yaw);
  d = vec3(d.x * cy + d.z * sy, d.y, -d.x * sy + d.z * cy);
  float u = atan(d.x, -d.z) / (2.0 * PI) + 0.5;
  float w = acos(clamp(d.y, -1.0, 1.0)) / PI;
  gl_FragColor = texture2D(tex, vec2(u, w));
}`;

const PV = { gl: null, loc: null, yaw: 0, pitch: 0, fov: 1.2, raf: 0 };
const FOV_MIN = 0.45, FOV_MAX = 1.9;   // about 26 to 109 degrees across

function panoStart(canvas, img) {
  const gl = canvas.getContext('webgl', { alpha: false, antialias: false })
          || canvas.getContext('experimental-webgl', { alpha: false });
  if (!gl) return false;

  const sh = (type, src) => {
    const o = gl.createShader(type);
    gl.shaderSource(o, src); gl.compileShader(o);
    if (!gl.getShaderParameter(o, gl.COMPILE_STATUS)) return null;
    return o;
  };
  const vs = sh(gl.VERTEX_SHADER, VSRC), fs = sh(gl.FRAGMENT_SHADER, FSRC);
  if (!vs || !fs) return false;
  const prog = gl.createProgram();
  gl.attachShader(prog, vs); gl.attachShader(prog, fs); gl.linkProgram(prog);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) return false;
  gl.useProgram(prog);

  const buf = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER,
    new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
  const a = gl.getAttribLocation(prog, 'a');
  gl.enableVertexAttribArray(a);
  gl.vertexAttribPointer(a, 2, gl.FLOAT, false, 0, 0);

  const tex = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, tex);
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, gl.RGB, gl.UNSIGNED_BYTE, img);
  // REPEAT across, so a drag past the seam comes round again; clamped
  // down, because there is nothing above the zenith to wrap to.
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);

  PV.gl = gl;
  PV.loc = {
    yaw: gl.getUniformLocation(prog, 'yaw'),
    pitch: gl.getUniformLocation(prog, 'pitch'),
    fov: gl.getUniformLocation(prog, 'fov'),
    aspect: gl.getUniformLocation(prog, 'aspect'),
  };
  PV.yaw = 0; PV.pitch = 0; PV.fov = 1.2;
  panoDraw();
  return true;
}

function panoDraw() {
  const gl = PV.gl;
  if (!gl) return;
  const c = gl.canvas;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const w = Math.round(c.clientWidth * dpr), h = Math.round(c.clientHeight * dpr);
  if (w && h && (c.width !== w || c.height !== h)) { c.width = w; c.height = h; }
  gl.viewport(0, 0, c.width, c.height);
  gl.uniform1f(PV.loc.yaw, PV.yaw);
  gl.uniform1f(PV.loc.pitch, PV.pitch);
  gl.uniform1f(PV.loc.fov, PV.fov);
  gl.uniform1f(PV.loc.aspect, (c.width || 1) / (c.height || 1));
  gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
}

/** Looking straight up or down in an equirectangular image smears, so stop short. */
function panoMove(dYaw, dPitch) {
  PV.yaw += dYaw;
  PV.pitch = Math.max(-1.45, Math.min(1.45, PV.pitch + dPitch));
  if (!PV.raf) PV.raf = requestAnimationFrame(() => { PV.raf = 0; panoDraw(); });
}
function panoZoom(f) {
  PV.fov = Math.max(FOV_MIN, Math.min(FOV_MAX, PV.fov * f));
  panoMove(0, 0);
}
function panoStop() {
  if (PV.raf) cancelAnimationFrame(PV.raf);
  PV.raf = 0; PV.gl = null; PV.loc = null;
}

/**
 * Dragging is not obvious and not everyone can do it accurately, so the
 * arrows are the primary control and the drag is the shortcut. Each arrow
 * is a full tap target and repeats while held.
 */
function panoWire(canvas) {
  let down = false, lx = 0, ly = 0, hold = 0;
  const scale = () => PV.fov / Math.max(canvas.clientWidth, 1) * 1.6;
  const start = ev => {
    const t = ev.touches ? ev.touches[0] : ev;
    down = true; lx = t.clientX; ly = t.clientY;
  };
  const move = ev => {
    if (!down) return;
    const t = ev.touches ? ev.touches[0] : ev;
    panoMove(-(t.clientX - lx) * scale(), (t.clientY - ly) * scale());
    lx = t.clientX; ly = t.clientY;
    ev.preventDefault();
  };
  const end = () => { down = false; };
  canvas.addEventListener('mousedown', start);
  canvas.addEventListener('mousemove', move);
  canvas.addEventListener('mouseup', end);
  canvas.addEventListener('mouseleave', end);
  canvas.addEventListener('touchstart', start, { passive: true });
  canvas.addEventListener('touchmove', move, { passive: false });
  canvas.addEventListener('touchend', end);
  canvas.addEventListener('wheel', ev => {
    panoZoom(ev.deltaY > 0 ? 1.1 : 0.9); ev.preventDefault();
  }, { passive: false });

  const STEP = 0.16;
  const act = {
    left: () => panoMove(-STEP, 0), right: () => panoMove(STEP, 0),
    up: () => panoMove(0, STEP), down: () => panoMove(0, -STEP),
    in: () => panoZoom(0.88), out: () => panoZoom(1.14),
  };
  const sheet = canvas.closest('#sheet') || document;
  sheet.querySelectorAll('[data-pan]').forEach(b => {
    const go = () => (act[b.dataset.pan] || (() => {}))();
    const begin = ev => {
      go();
      clearInterval(hold);
      hold = setInterval(go, 140);
      ev.preventDefault();
    };
    const stop = () => clearInterval(hold);
    b.addEventListener('mousedown', begin);
    b.addEventListener('touchstart', begin, { passive: false });
    ['mouseup', 'mouseleave', 'touchend', 'touchcancel']
      .forEach(e => b.addEventListener(e, stop));
  });
  canvas.tabIndex = 0;
  canvas.addEventListener('keydown', ev => {
    const k = { ArrowLeft: 'left', ArrowRight: 'right', ArrowUp: 'up',
                ArrowDown: 'down', '+': 'in', '-': 'out' }[ev.key];
    if (k) { act[k](); ev.preventDefault(); }
  });
}

/**
 * The pane, opened from a place. Lazy on purpose: a photosphere is a
 * quarter of a megabyte and most readers will never open one, so nothing
 * is fetched until somebody asks to look.
 */
async function lookAround(name) {
  const host = document.getElementById('panoHost');
  if (!host) return;
  let p;
  try { p = (await lazy.pano())[name]; }
  catch {
    host.innerHTML = `<p class="pa">The list of photospheres would not load.${
      navigator.onLine ? '' : ' You are offline, and this one has not been downloaded.'}</p>`;
    return;
  }
  if (!p) {
    host.innerHTML = `<p class="pa">Nobody has taken a photosphere of
      ${esc(name)}, or near enough to count.</p>`;
    return;
  }
  host.innerHTML = `
    <div class="pano"><canvas id="panoC" aria-label="A photosphere of ${esc(name)}.
      Drag it, or use the arrows below."></canvas>
      <p class="pano-load">Loading the photosphere…</p></div>
    <div class="pano-ctl">
      <button class="pbtn" data-pan="left"  aria-label="Look left">←</button>
      <button class="pbtn" data-pan="up"    aria-label="Look up">↑</button>
      <button class="pbtn" data-pan="down"  aria-label="Look down">↓</button>
      <button class="pbtn" data-pan="right" aria-label="Look right">→</button>
      <button class="pbtn" data-pan="in"    aria-label="Closer">+</button>
      <button class="pbtn" data-pan="out"   aria-label="Wider">−</button>
    </div>
    <p class="pa" id="panoNote">Drag the picture, or hold an arrow.</p>`;

  const canvas = document.getElementById('panoC');
  const img = new Image();
  img.decoding = 'async';
  img.onload = () => {
    const box = canvas.parentElement.querySelector('.pano-load');
    if (box) box.remove();
    if (panoStart(canvas, img)) {
      panoWire(canvas);
    } else {
      // No WebGL at all. The flat image is still the whole view, just
      // unrolled, and saying so beats an empty box.
      canvas.parentElement.innerHTML =
        `<img src="${esc('data/pano/' + p.file)}" alt="A photosphere of ${esc(name)},
          shown flat" style="width:100%;height:auto;display:block">`;
      const note = document.getElementById('panoNote');
      if (note) note.textContent = 'This phone cannot wrap the picture round ' +
        'you, so here it is unrolled flat. The left and right edges join up.';
      const ctl = document.querySelector('.pano-ctl');
      if (ctl) ctl.remove();
    }
    const note = document.getElementById('panoNote');
    if (note && PV.gl) {
      note.innerHTML = `Drag the picture, or hold an arrow. ${
        p.km != null && p.km > 0.2
          ? `Taken about ${p.km < 1 ? Math.round(p.km * 1000) + ' m'
             : p.km + ' km'} from the spot itself. `
          : ''}${esc(p.artist || 'A Mapillary contributor')}${
        p.taken ? ', ' + esc(String(p.taken).slice(0, 10)) : ''} · ${
        esc(p.licence || 'CC BY-SA 4.0')}${
        p.page ? ` · <a href="${esc(p.page)}" target="_blank" rel="noopener">source</a>` : ''}`;
    }
  };
  img.onerror = () => {
    host.innerHTML = `<p class="pa">The photosphere would not load.${
      navigator.onLine ? '' : ' You are offline, and this one has not been downloaded.'}</p>`;
  };
  img.src = 'data/pano/' + p.file;
}


/* ============================================================== install */
/* Chrome hands over a prompt it will honour; Safari never does, and the
   only way in is Share then Add to Home Screen. So the offer is a real
   button where there is a real prompt, and the right words for this phone
   where there is not - not a list of every platform's instructions, which
   is how nobody ever installs anything. */

let INSTALL_PROMPT = null;
window.addEventListener('beforeinstallprompt', ev => {
  ev.preventDefault();
  INSTALL_PROMPT = ev;
  const b = document.getElementById('installBtn');
  if (b) b.hidden = false;
});

function standalone() {
  try {
    return window.matchMedia('(display-mode: standalone)').matches
        || window.navigator.standalone === true;
  } catch { return false; }
}

/** The one route that works on the phone in front of us. */
function installHow() {
  const ua = navigator.userAgent || '';
  const ios = /iPad|iPhone|iPod/.test(ua)
           || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1);
  if (ios) {
    return 'Tap the share button at the bottom of Safari \u2014 the square '
         + 'with an arrow coming out of it \u2014 then scroll down and tap '
         + '<b>Add to Home Screen</b>.';
  }
  if (/Android/.test(ua)) {
    return 'Tap the three dots at the top right of the browser, then '
         + '<b>Add to Home screen</b> or <b>Install app</b>.';
  }
  return 'Your browser\u2019s menu will have <b>Install</b> or '
       + '<b>Add to Home screen</b> in it.';
}

function installBlock() {
  if (standalone()) {
    return `<div class="mo"><p style="font-weight:600;margin:0 0 6px">It is
      already on your home screen</p><p class="de" style="margin:0">That is
      why there are no browser bars round it, and why it opens straight to
      where you were.</p></div>`;
  }
  return `<div class="mo">
    <p style="font-weight:600;margin:0 0 6px">Put it on your home screen</p>
    <p class="de" style="margin:0 0 8px">Then it is an icon you tap like any
    other app, it opens straight to where you left off, and the browser\u2019s
    bars go away \u2014 which is a good inch of screen back for the words.
    Nothing is installed from a shop and nothing asks for an account.</p>
    <button class="instbtn" id="installBtn" data-install="1" hidden>Add it to
      my home screen</button>
    <p class="pa" style="margin:8px 0 0">${installHow()}</p></div>`;
}

async function doInstall() {
  if (!INSTALL_PROMPT) return;
  const p = INSTALL_PROMPT;
  INSTALL_PROMPT = null;
  const b = document.getElementById('installBtn');
  if (b) b.hidden = true;
  try { await p.prompt(); } catch { /* dismissed */ }
}

/* ============================================================== welcome */
/* The first thing a person sees when somebody sends them the link.
   Two sentences on what it is, then the five things worth knowing, each
   one showing the button it is talking about rather than naming it. Then
   out of the way: it appears once, and after that only if asked for. */

function seenWelcome() {
  try { return localStorage.getItem('codex-seen') === '1'; } catch { return false; }
}
function markWelcome() {
  try { localStorage.setItem('codex-seen', '1'); } catch { /* private mode */ }
}

const ICON_AA = `<span class="demo"><span style="font-weight:600">A</span><span
  style="font-weight:600;font-size:.72em">a</span></span>`;
const ICON_BOOKS = `<span class="demo"><svg width="19" height="19" viewBox="0 0 24 24"
  fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round"
  aria-hidden="true"><path d="M4 5h16M4 12h16M4 19h16"/></svg></span>`;
const ICON_SEARCH = `<span class="demo"><svg width="19" height="19" viewBox="0 0 24 24"
  fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round"
  aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.4 15.4 21 21"/></svg></span>`;

function welcomeView() {
  const o = [];
  o.push(`<h1 style="font-size:1.5rem;margin:14px 0 4px;line-height:1.3">The Jarrell Codex</h1>`);
  o.push(`<p class="ot" style="margin:0 0 20px">A Bible you can read, listen to,
    and look things up in</p>`);

  o.push(`<p class="de" style="font-size:var(--t4)">The whole Bible in English,
    with the Hebrew and Greek it was written in underneath, and a way to look up
    any word, place, person or date in it.</p>`);
  o.push(`<p class="de">It is free, there is nothing to install, no account, and
    nothing here watches what you read.</p>`);

  o.push(`<p class="lbl" style="margin:26px 0 10px">Five things worth knowing</p>`);

  const tip = (demo, head, body) => `<div class="tip">
    <div class="tip-d">${demo}</div>
    <div><p class="tip-h">${head}</p><p class="de" style="margin:4px 0 0">${body}</p></div>
  </div>`;

  o.push(tip(
    `<span class="demo"><svg width="20" height="20" viewBox="0 0 24 24"
      fill="currentColor" aria-hidden="true"><path d="M8 5v14l11-7z"/></svg></span>`,
    'It can read itself to you',
    `Every chapter has a <b>Listen</b> button at the top and the bottom. The
     recordings are read by volunteers and cost nothing. That one needs an
     internet connection; everything else does not.`));

  o.push(tip(ICON_AA,
    'You can make the words bigger',
    `Tap <b>Aa</b> at the top for text size and colour. It goes a good deal
     larger than it starts, and there are six colour schemes including a dark
     one for reading at night. Whatever you pick is remembered.`));

  o.push(tip(
    `<span class="demo" style="font-family:var(--grk);font-size:1.15rem">\u03bb\u03cc\u03b3</span>`,
    'Tap any Hebrew or Greek word',
    `It opens up: what the word is, what its parts mean, its dictionary number,
     and every other verse in the Bible that uses it.`));

  o.push(tip(
    `<span class="demo">\u25cc</span>`,
    'A few places you can stand in',
    `Where somebody has left a full 360\u00b0 photograph \u2014 Mount Sinai,
     Nazareth, Bethlehem, Hebron, Jericho and about twenty more \u2014 the place
     panel lets you turn round on the spot and look at the hills. Arrows,
     or drag it with your thumb.`));

  o.push(tip(
    `<span class="demo" style="color:var(--accent)">\u25c6</span>`,
    'Tap the little markers under a verse',
    `They lead to the place and what it looks like today, the people, the date
     by several different reckonings, the translators' notes, the other verses
     that say the same thing, and six old commentaries.`));

  o.push(tip(ICON_BOOKS + ICON_SEARCH,
    'Getting around',
    `The lines at the top left open the list of books. The name of the chapter,
     in the middle, jumps to any chapter. The magnifying glass searches the
     whole Bible.`));

  o.push(`<div style="margin:30px 0 10px">
    <button class="start" data-startreading="1">Start reading \u2192</button></div>`);
  o.push(`<p class="pa" style="margin:4px 0 0">It opens at John 3. Use the
    menu at the top left to go anywhere else.</p>`);

  o.push(`<p class="lbl" style="margin:30px 0 8px">Three more things, for later</p>`);
  o.push(installBlock());
  o.push(`<div class="mo"><p style="font-weight:600;margin:0 0 6px">It works with no signal</p>
    <p class="de" style="margin:0">Chapters you have opened are kept on your phone
    already. If you want the whole thing \u2014 every word, every picture \u2014 there is a
    download button on the About page. Then it works on a plane, in a hospital, or
    anywhere with no bars at all.</p></div>`);
  o.push(`<div class="mo"><p style="font-weight:600;margin:0 0 6px">Nothing here is
    anyone's opinion dressed up as fact</p>
    <p class="de" style="margin:0">Where the experts disagree \u2014 about a date, or
    where a place actually was \u2014 it says so and shows you the disagreement, rather
    than picking one and keeping quiet. Every source is named and free to copy.</p></div>`);

  o.push(`<button class="more" data-go="about" style="margin-top:20px">About, and
    where all of this came from \u2192</button>`);
  o.push(footer());
  $('#view').innerHTML = o.join('');
  window.scrollTo(0, 0);
}

/* =============================================================== plates */
/* All 150 of Dore's engravings, in the order he published them, with an
   honest account of each one.

   125 sit at a verse in the text. 20 illustrate Tobit, Judith, Baruch, the
   Greek additions to Daniel and the Maccabees, which this Bible does not
   carry - they are shown here rather than dropped, because the reader is
   entitled to see what the set contains and to be told why those plates
   are not in the text. Five carry no reference at all: Commons records
   none, and rather than guess a verse from the title they are listed as
   what they are. Dore's own numbering puts each one where it belongs in
   the sequence, which is the only placement anyone can vouch for. */

async function platesView() {
  if (!S.dore) { try { await lazy.dore(); } catch { S.dore = null; } }
  if (!S.dore) {
    $('#view').innerHTML = `<p class="load">The list of engravings would not load.
      If you are offline, download the engravings from the offline page first.</p>`;
    return;
  }
  const d = S.dore;
  const where = {};
  Object.keys(d.at || {}).forEach(vk => (d.at[vk] || []).forEach(pid => where[pid] = vk));
  const apoc = d.apoc || {};
  const ids = Object.keys(d.plates || {}).sort((a, b) => (+a) - (+b));
  const placed = ids.filter(k => where[k]).length;
  const outside = ids.filter(k => !where[k] && apoc[k]).length;
  const nowhere = ids.length - placed - outside;

  const o = [];
  o.push(`<h1 style="font-size:1.3rem;margin:6px 0 2px">Dor\u00e9's engravings</h1>`);
  o.push(`<p class="ot" style="margin:0 0 14px">${ids.length} plates, engraved in 1866
    &middot; all public domain</p>`);
  o.push(`<p class="de">Gustave Dor\u00e9 cut these for an illustrated Bible published
    in 1866. He died in 1883, so they have been free for anyone to use for a
    century. They are one Victorian artist's reading of the scene \u2014 not a
    photograph, and not evidence \u2014 but he was very good, and where the
    printer said which passage a plate belongs to, it sits there in the text.</p>`);
  o.push(`<p class="pa" style="margin:10px 0 18px">${placed} are set at a verse.
    ${outside} illustrate books this Bible does not carry, so they are here and
    not in the text. ${nowhere} carry no reference at all; rather than guess a
    verse from the title, they are listed as what they are.</p>`);

  ids.forEach(k => {
    const pl = d.plates[k];
    if (!pl) return;
    const vk = where[k];
    o.push(`<figure class="plate" style="margin:18px 0 26px">
      <img src="data/dore/${esc(pl.file)}" alt="${esc(pl.title)}, engraved by Gustave Dor\u00e9"
        width="${pl.w}" height="${pl.h}" loading="lazy" decoding="async">
      <figcaption>
        <span style="font-weight:600">${esc(pl.title)}</span>
        <span class="ot" style="display:block;margin-top:3px">Plate ${esc(k)}${
          pl.ref ? ' \u00b7 printed as \u201c' + esc(pl.ref) + '\u201d' : ''}</span>
        ${vk ? `<button class="chip" data-ref="${esc(vk)}"
                 style="margin-top:8px">Read ${esc(refLabel(vk))} \u2192</button>`
             : `<span class="ot" style="display:block;margin-top:6px">${
                 apoc[k] ? 'Illustrates ' + esc(apoc[k]) + '.'
                         : 'No passage is recorded for this plate, so it is not set in the text.'
               }</span>`}
        ${pl.page ? `<span class="ot" style="display:block;margin-top:4px"><a
          href="${esc(pl.page)}" target="_blank" rel="noopener">Where this scan came from</a></span>` : ''}
      </figcaption></figure>`);
  });
  o.push(footer());
  $('#view').innerHTML = o.join('');
  window.scrollTo(0, 0);
}

/* ================================================================= audio */
/* Public-domain readings from LibriVox, streamed from archive.org. Nothing
   is hosted here and nothing is downloadable for offline use, so the player
   says plainly that it needs a connection rather than failing silently.

   Most readings put many chapters in one file - the complete-Bible set runs
   to 32 chapters of Psalms in a single half-hour track. A reader on Psalm 23
   dropped at Psalm 1 with no idea where to drag has been given a worse tool
   than no player at all, so the file's chapter list and each chapter's verse
   count are used to estimate where the chapter starts. It is an estimate
   from verse counts, not a timing anyone recorded, and it is labelled as
   one every time it is offered. */

const AU = { fi: null, key: null, seek: null, wired: false };

function auEl() { return document.getElementById('plAudio'); }

/** Proportional position of a chapter inside its file, 0..1. */
function auFraction(f, i) {
  const total = f.vs.reduce((a, b) => a + b, 0);
  if (!total || i <= 0) return 0;
  let before = 0;
  for (let k = 0; k < i; k++) before += f.vs[k];
  return before / total;
}

function auClock(sec) {
  if (!isFinite(sec) || sec < 0) return '';
  const m = Math.floor(sec / 60), ss = Math.floor(sec % 60);
  return m + ':' + ('0' + ss).slice(-2);
}

async function listen(book, ch) {
  const key = book + '.' + ch;
  const bar = document.getElementById('player');
  const txt = document.getElementById('plTxt');
  const note = document.getElementById('plNote');
  if (!bar || !txt || !note) return;
  bar.hidden = false;
  document.body.classList.add('playing');
  txt.innerHTML = '<b>Finding a reading\u2026</b>';
  note.innerHTML = '';

  let a;
  try { a = await lazy.audio(); }
  catch {
    txt.innerHTML = '<b>The list of readings would not load.</b>';
    note.textContent = navigator.onLine
      ? 'Try again in a moment.'
      : 'You are offline. The readings are streamed, so they need a connection.';
    return;
  }
  const place = (a.chapters || {})[key];
  if (!place) {
    txt.innerHTML = '<b>No recording for ' + esc(refLabel(key)) + '.</b>';
    note.textContent = 'Every other chapter has one, so this is worth reporting.';
    return;
  }
  const [fi, i] = place;
  const f = a.files[fi];
  const src = (a.sources || {})[f.item] || {};
  const el = auEl();
  if (!el) return;

  AU.key = key;
  const same = AU.fi === fi && el.src === f.u;
  if (!same) {
    AU.fi = fi;
    AU.seek = null;
    el.src = f.u;
  }

  const first = f.ch[0], last = f.ch[f.ch.length - 1];
  const span = f.ch.length > 1
    ? refLabel(first) + ' \u2013 ' + refLabel(last).replace(/^\D+/, '').trim()
    : refLabel(first);

  txt.innerHTML = '<b>' + esc(refLabel(key)) + '</b>' +
    (f.ch.length > 1
      ? '<span class="pl-sub">One recording covers ' + esc(span) +
        ' \u2014 ' + f.ch.length + ' chapters, ' + f.mb + '\u00a0MB</span>'
      : '<span class="pl-sub">A recording of this chapter on its own</span>');

  const bits = [];
  if (!navigator.onLine)
    bits.push('<b>You are offline.</b> The readings are streamed from archive.org, ' +
      'so this one cannot play until you have a connection. The text itself ' +
      'still works offline.');
  if (f.ch.length > 1 && i > 0)
    bits.push('<span id="plEst">Starting at an estimated position for ' +
      esc(refLabel(key)) + '. It is worked out from verse counts, not a real ' +
      'timing, so drag the slider a little either way if it lands in the ' +
      'wrong place.</span> <button class="pl-b" data-aufrom="0">Start at ' +
      esc(refLabel(first)) + ' instead</button>');
  bits.push('Read by volunteers for ' +
    (src.page ? '<a href="' + esc(src.page) + '" target="_blank" rel="noopener">LibriVox</a>'
              : 'LibriVox') +
    '. Public domain. Streamed from archive.org, not stored here.');
  note.innerHTML = bits.map(b => '<span class="pl-line">' + b + '</span>').join('');

  if (!same && f.ch.length > 1 && i > 0) {
    AU.seek = auFraction(f, i);
    el.addEventListener('loadedmetadata', auSeek, { once: true });
  }
  auSession(key, f, src);

  // An audio Bible that stops dead at the end of Genesis 14 and waits to be
  // asked is not much use to someone listening with the phone down. The
  // files are in canonical order, so carry on into the next one and say in
  // the bar where it has got to.
  if (!AU.wired) {
    AU.wired = true;
    el.addEventListener('ended', auNext);
  }
  el.play().catch(() => {
    const e = document.getElementById('plEst');
    if (!navigator.onLine) return;
    if (e) e.textContent = 'Press play to start.';
  });
}

/** The next file in canonical order, when one ends. */
async function auNext() {
  const a = S.audio;
  if (!a || AU.fi == null) return;
  const next = a.files[AU.fi + 1];
  if (!next) {
    const note = document.getElementById('plNote');
    if (note) note.innerHTML = '<span class="pl-line">That is the end of ' +
      'Revelation, and the end of the readings.</span>';
    return;
  }
  const key = next.ch[0];
  const p = key.split('.');
  AU.fi = null;                       // force a reload of the new file
  await listen(p[0], +p[1]);
  const note = document.getElementById('plNote');
  if (note) note.insertAdjacentHTML('afterbegin',
    '<span class="pl-line">The last reading finished, so this one carried ' +
    'on from it.</span>');
}

/* The lock screen is the only control a listener has once the phone is in
   their pocket, so put the chapter and the controls there. Everything here
   is optional in the browser and all of it is wrapped: an older phone that
   has none of it still plays the reading. */
function auSession(key, f, src) {
  const ms = navigator.mediaSession;
  if (!ms) return;
  try {
    ms.metadata = new MediaMetadata({
      title: refLabel(key),
      artist: 'Read by volunteers for LibriVox',
      album: f.ch.length > 1
        ? 'In a reading of ' + refLabel(f.ch[0]) + '\u2013' +
          f.ch[f.ch.length - 1].split('.')[1]
        : 'The Jarrell Codex',
    });
  } catch { /* no MediaMetadata on this browser */ }
  const set = (action, fn) => {
    try { ms.setActionHandler(action, fn); } catch { /* unsupported action */ }
  };
  const el = auEl();
  set('play', () => { if (el) el.play().catch(() => {}); });
  set('pause', () => { if (el) el.pause(); });
  set('stop', auStop);
  set('seekbackward', () => { if (el) el.currentTime = Math.max(0, el.currentTime - 30); });
  set('seekforward', () => { if (el) el.currentTime += 30; });
}

/** Only once the file's length is known can a fraction become a position. */
function auSeek() {
  const el = auEl();
  if (!el || AU.seek == null || !isFinite(el.duration)) return;
  const t = el.duration * AU.seek;
  try { el.currentTime = t; } catch { return; }
  const e = document.getElementById('plEst');
  if (e) e.textContent = 'Started at about ' + auClock(t) + ', an estimate for ' +
    refLabel(AU.key) + ' worked out from verse counts rather than a real ' +
    'timing. Drag the slider a little either way if it lands in the wrong place.';
}

function auStop() {
  const el = auEl();
  if (el) { el.pause(); el.removeAttribute('src'); el.load(); }
  try {
    if (navigator.mediaSession) {
      navigator.mediaSession.metadata = null;
      navigator.mediaSession.playbackState = 'none';
    }
  } catch { /* ignore */ }
  AU.fi = AU.key = AU.seek = null;
  const bar = document.getElementById('player');
  if (bar) bar.hidden = true;
  document.body.classList.remove('playing');
}

/* ============================================================= chronology */
function spanLabel(s) {
  return bookName(s[0]) + ' ' + s[1] + ':' +
    (s[2] === s[3] ? s[2] : s[2] + '–' + s[3]);
}
async function chronoView() {
  await Promise.all([lazy.event(), S.order || get('chrono_order.json').then(d => S.order = d)]);
  const sch = (S.chron.schemes || []).find(s => s.scheme_id === S.chrono) || {};
  const ord = (S.order.order || {})[S.chrono] || { dated: [], undated: [] };
  const o = [];
  o.push(`<h1 style="font-size:1.3rem;margin:6px 0 2px">The story in order</h1>`);
  o.push(`<p class="ot" style="margin:0 0 14px">${ord.dated.length} dated events
    &middot; ${S.order.order ? Object.keys(S.order.order).length : 0} schemes to choose from</p>`);
  o.push(`<p class="lbl">Chronology</p>
    <div class="opts" style="margin-bottom:10px">${(S.chron.schemes || []).map(s =>
      `<button class="opt ${s.scheme_id === S.chrono ? 'on' : ''}" data-setscheme2="${esc(s.scheme_id)}">${
        s.scheme_id === S.chrono ? '\u2713 ' : ''}${esc(s.name)}${
        s.coverage === 'full' ? '' : ' — partial'}</button>`).join('')}</div>`);
  if (sch.summary) o.push(`<p class="de" style="color:var(--ink-soft)">${esc(sch.summary)}</p>`);
  if (sch.source) o.push(`<p class="oc">${esc(sch.source)}</p>`);

  if (ord.dated.length < 50) {
    o.push(`<div style="border:1px solid var(--warn);border-radius:10px;padding:12px;margin:14px 0">
      <p class="de" style="margin:0"><b>This scheme only anchors ${ord.dated.length}
      event${ord.dated.length === 1 ? '' : 's'}.</b> Its published work fixes a handful
      of dates and leaves the rest to be worked out from them, so there is no full
      ordering to show. The events below the dated ones are in the order the text
      tells them, not in a date order this scheme would vouch for. For a complete
      dated sequence, pick Floyd Nolen Jones.</p></div>`);
  }
  o.push(`<button class="more" data-go="about">Why do the schemes disagree? →</button>`);

  const row = eid => {
    const e = S.event[eid]; if (!e) return '';
    const dt = (e.dates || {})[S.chrono];
    const y = dt ? yearLabel(dt[0]) : null;
    const end = dt && dt[1] != null && dt[1] !== dt[0] ? yearLabel(dt[1]) : null;
    const sp = (S.order.spans || {})[eid] || [];
    const first = sp[0];
    return `<button class="hit" ${first ? `data-ref="${esc(first[0] + '.' + first[1] + '.' + first[2])}"` : ''}>
      <span class="r">${y ? esc(y + (end ? ' – ' + end : '')) : '—'}</span>
      <span class="t" style="color:var(--ink);font-size:1rem">${esc(e.title)}</span>
      ${sp.length ? `<span class="t">${sp.slice(0, 4).map(s => esc(spanLabel(s))).join(' &middot; ')}${
        sp.length > 4 ? ' &middot; +' + (sp.length - 4) + ' more' : ''}</span>` : ''}</button>`;
  };
  o.push(`<p class="lbl" style="margin:22px 0 6px">Dated in this scheme</p>`);
  o.push(ord.dated.map(row).join('') || '<p class="pa">None.</p>');
  if (ord.undated.length) {
    o.push(`<p class="lbl" style="margin:22px 0 6px">Undated here — in narrative order</p>`);
    o.push(ord.undated.map(row).join(''));
  }
  o.push(footer());
  $('#view').innerHTML = o.join('');
  window.scrollTo(0, 0);

}

/* ================================================================== about */
function aboutView() {
  const o = [];
  o.push(`<h1 style="font-size:1.35rem;margin:6px 0 14px">About this Bible</h1>`);
  o.push(`<p class="de">Every word of the Hebrew, Aramaic and Greek is tagged with its
    dictionary number and its grammar. Tap any word to see its parts, what each part
    means, and every other verse that uses it. Tap the markers under a verse for the
    place, the people, the event, the translators’ notes, and the cross-references.
    Nothing here costs anything and nothing here tracks you.</p>`);

  o.push(`<p class="lbl" style="margin:24px 0 8px">Why the dates disagree</p>`);
  (S.chron.notes || []).forEach(n => {
    o.push(`<div class="mo"><p style="font-weight:600;margin:0 0 6px">${esc(n.heading)}</p>
      <p class="de" style="margin:0;white-space:pre-wrap">${esc(n.body)}</p></div>`);
  });
  o.push(`<p class="lbl" style="margin:24px 0 8px">The schemes on offer</p>`);
  (S.chron.schemes || []).forEach(s => {
    o.push(`<div class="mo"><p style="font-weight:600;margin:0 0 6px">${esc(s.name)}
      <span class="ot">${esc(s.coverage)}</span></p>
      <p class="de" style="margin:0">${esc(s.summary || '')}</p>
      ${s.source ? `<p class="oc">${esc(s.source)}</p>` : ''}</div>`);
  });

  o.push(`<p class="lbl" style="margin:24px 0 8px">Greek pronunciation</p>`);
  o.push(`<p class="de">There is no single right answer, so all three are here.
    Switch between them in Settings.</p>`);
  Object.entries(PRON).forEach(([k, v]) => o.push(
    `<div class="mo"><p style="font-weight:600;margin:0 0 6px;text-transform:capitalize">${esc(k)}</p>
     <p class="de" style="margin:0">${esc(v)}</p></div>`));

  o.push(`<p class="lbl" style="margin:24px 0 8px">Audio</p>`);
  o.push(`<p class="de">Not here yet. Spoken-word recordings need a licence from the
    people who made them, and that request is still outstanding. Everything else
    works without it.</p>`);

  o.push(installBlock());
  o.push(`<button class="more" data-go="welcome" style="margin:18px 0 0">Show me
    how to use this again \u2192</button>`);
  o.push(`<p class="lbl" style="margin:24px 0 8px">Where all of this came from</p>`);
  [['STEPBible — Tyndale House, Cambridge',
    'TAHOT and TAGNT: the Hebrew and Greek text with a dictionary number and a grammar code on every word, including the separate numbers for prefixes and endings. CC BY 4.0.'],
   ['Brown-Driver-Briggs, Thayer, Abbott-Smith, Liddell-Scott-Jones',
    'The lexicon entries behind each number. Public domain, via STEPBible and the Perseus Digital Library.'],
   ['OpenBible.info', 'Place coordinates with an honest confidence figure, and the cross-reference weights. CC BY 4.0.'],
   ['Theographic Bible Metadata', 'People, events, and Easton’s Bible Dictionary. CC BY 4.0.'],
   ['unfoldingWord', 'Translation Notes — verse-by-verse notes on wording, idiom and background. CC BY-SA 4.0.'],
   ['MACULA', 'Syntactic and semantic annotation of the original text. CC BY 4.0.'],
   ['Matthew Henry, the Geneva notes, Calvin, Poole, Trapp, Spurgeon',
    'Six commentaries written between 1599 and 1885, keyed to the verse. All public domain. A seventh source of patristic quotations was left out: its English translations are described as “19th-century and later”, and anything whose copyright cannot be settled does not belong in a Bible meant to be copied and handed out.'],
   ['King James, American Standard, Young’s Literal, Darby', 'English translations. All public domain.'],
   ['LibriVox, via archive.org',
    'The spoken readings behind the Listen control — every chapter of all 66 books, read by volunteers and released into the public domain. Nothing is stored here: the files stream from archive.org, so they need a connection even when the text does not.'],
   ['Wikimedia Commons and Wikidata',
    'The photographs of the places. Each one carries its own licence and photographer where it appears; none were used that are not free to pass on.'],
   ['Mapillary, via Wikimedia Commons',
    'The 25 full 360\u00b0 photospheres \u2014 the places you can stand in and turn round. Somebody walked up there with a camera and gave the picture away, which is why Mount Sinai is in and most places are not: the coverage follows roads and footpaths. Each one names who took it, how far from the spot it was taken, and links its page. Nearly all CC BY-SA 4.0.'],
   ['Gustave Doré, 1866',
    'The 150 engravings. Doré died in 1883, so the plates have been in the public domain for a century; these scans come from Wikimedia Commons. 125 are set at the verse the printer named; the rest are in the gallery, each with the reason it is not in the text.']
  ].forEach(([t, b]) => o.push(
    `<div class="mo"><p style="font-weight:600;margin:0 0 6px">${esc(t)}</p>
     <p class="de" style="margin:0">${esc(b)}</p></div>`));

  o.push(`<p class="lbl" style="margin:24px 0 8px">Take the whole thing</p>`);
  o.push(`<p class="de">Everything behind this page is one database you can
    download and keep. It needs no connection, no account and no permission.
    Put it on a memory stick and hand it to somebody.</p>`);
  o.push(`<div class="mo"><p style="font-weight:600;margin:0 0 6px">The Bible</p>
    <p class="de" style="margin:0 0 8px">Text, parsing, lexicons, translations,
    places, people, events, dates, dictionary, notes and cross-references.
    132 MB to download, 456 MB once unpacked. It comes in two pieces because
    GitHub will not host a single file this big \u2014 take both, then join
    them.</p>
    <a class="more" style="display:block" href="download/bible.db.gz.part00"
       download>Download part 1 of 2 \u00b7 90 MB \u2193</a>
    <a class="more" style="display:block" href="download/bible.db.gz.part01"
       download>Download part 2 of 2 \u00b7 42 MB \u2193</a>
    <p class="oc" style="margin-top:10px">Mac or Linux:</p>
    <p class="de" style="font-family:var(--mono);font-size:.76rem;
       background:var(--accent-soft);padding:9px;border-radius:7px;
       overflow-x:auto;white-space:pre">cat bible.db.gz.part* > bible.db.gz
gunzip bible.db.gz</p>
    <p class="oc">Windows:</p>
    <p class="de" style="font-family:var(--mono);font-size:.76rem;
       background:var(--accent-soft);padding:9px;border-radius:7px;
       overflow-x:auto;white-space:pre">copy /b bible.db.gz.part00 + bible.db.gz.part01 bible.db.gz</p>
    </div>`);
  o.push(`<div class="mo"><p style="font-weight:600;margin:0 0 6px">The commentaries</p>
    <p class="de" style="margin:0 0 8px">All six, keyed to the verse. Separate
    file, so you can skip it if you are short of room. 48 MB to download,
    148 MB unpacked.</p>
    <a class="more" style="display:inline-block" href="download/commentary.db.gz"
       download>Download commentary.db.gz \u2193</a></div>`);
  o.push(`<p class="oc">Both are plain SQLite. Checksums in
    <a href="download/SHA256SUMS.txt">SHA256SUMS.txt</a>.</p>`);

  o.push(`<p class="lbl" style="margin:24px 0 8px">Licence</p>`);
  o.push(`<p class="de">The code is MPL-2.0. The assembled data is CC BY-SA 4.0,
    because unfoldingWord’s notes are share-alike and that carries. Take it,
    copy it, hand it out. Source at
    <a href="https://github.com/jebjarrell1974-debug/jarrell-codex">github.com/jebjarrell1974-debug/jarrell-codex</a>.</p>`);
  o.push(`<p class="de" style="color:var(--ink-faint)">The Jarrell Codex.</p>`);
  $('#view').innerHTML = o.join('');
  window.scrollTo(0, 0);
}

/* ================================================= books, settings, router */
function booksSheet() {
  const o = [`<p class="lbl">Books</p>`];
  ['OT', 'NT'].forEach(t => {
    o.push(`<p class="lbl" style="margin:14px 0 8px">${t === 'OT' ? 'Old Testament' : 'New Testament'}</p>`);
    o.push('<div class="blist">');
    S.books.filter(b => b[2] === t).forEach(b => o.push(
      `<button data-book="${esc(b[0])}">${esc(bookName(b[0]))}
       <span class="ot">${b[3]}</span></button>`));
    o.push('</div>');
  });
  sheet(o.join(''));
}
function chaptersSheet(book) {
  const meta = S.bookIx[book];
  const o = [`<p class="lbl">${esc(bookName(book))} — ${meta.chapters} chapters</p>`,
             '<div class="grid">'];
  for (let i = 1; i <= meta.chapters; i++)
    o.push(`<button data-ch="${i}" data-cbook="${esc(book)}">${i}</button>`);
  o.push('</div>');
  sheet(o.join(''));
}
function settingsSheet() {
  const o = [`<p class="lbl">Settings</p>`];
  o.push(`<button class="opt" data-go2="display" style="margin-bottom:18px">
    Text size and brightness \u2192</button>`);
  o.push(`<p class="lbl" style="margin-top:12px">English translation</p>
    <div class="opts">${Object.entries(TX).map(([k, v]) =>
      `<button class="opt ${S.tx === k ? 'on' : ''}" data-settx="${k}">${
        S.tx === k ? '\u2713 ' : ''}${esc(v)}</button>`).join('')}</div>`);
  o.push(`<p class="lbl" style="margin-top:18px">Greek pronunciation</p>
    <div class="opts">${Object.keys(PRON).map(k =>
      `<button class="opt ${S.pron === k ? 'on' : ''}" data-setpron="${k}">${
        S.pron === k ? '\u2713 ' : ''}${k[0].toUpperCase() + k.slice(1)}</button>`).join('')}</div>
    <p class="pa">${esc(PRON[S.pron])}</p>`);
  o.push(`<p class="lbl" style="margin-top:18px">Chronology</p>
    <div class="opts">${(S.chron.schemes || []).map(s =>
      `<button class="opt ${s.scheme_id === S.chrono ? 'on' : ''}" data-setscheme="${esc(s.scheme_id)}">${
        s.scheme_id === S.chrono ? '\u2713 ' : ''}${esc(s.name)}</button>`).join('')}</div>`);
  o.push(`<label class="lbl" style="margin-top:16px">Original language</label>
    <button class="chip" id="origTgl" style="margin-top:4px">${S.showOrig ?
      '✓ showing Hebrew / Greek' : 'hidden — English only'}</button>`);
  o.push(`<button class="more" data-go="offline" style="margin-top:22px">Keep it offline — download the whole Bible →</button>`);
  o.push(`<button class="more" data-go="about">About, sources and licences →</button>`);
  sheet(o.join(''));
  // buttons now, handled by delegation - a <select> defeated every older
  // participant Sayago & Blat tested, while larger tappable controls did not
  $('#origTgl').onclick = () => { S.showOrig = !S.showOrig; save(); renderChapter(); settingsSheet(); };
}

function save() {
  try {
    localStorage.setItem('codex', JSON.stringify(
      { tx: S.tx, scheme: S.scheme, chrono: S.chrono, pron: S.pron,
        showOrig: S.showOrig, book: S.book, ch: S.ch, fs: S.fs,
        showPix: S.showPix }));
  } catch { /* private mode, blocked storage — settings just don't persist */ }
}
function load() {
  try {
    const v = JSON.parse(localStorage.getItem('codex') || '{}');
    if (v && typeof v === 'object') Object.assign(S, {
      tx: TX[v.tx] ? v.tx : S.tx,
      chrono: v.chrono || S.chrono,
      pron: PRON[v.pron] ? v.pron : S.pron,
      showOrig: v.showOrig !== false,
      book: v.book || S.book, ch: v.ch || S.ch,
      fs: Math.min(FS_MAX, Math.max(FS_MIN, +v.fs || S.fs)),
      scheme: SCHEME_ORDER.indexOf(v.scheme) >= 0 ? v.scheme : S.scheme,
      showPix: v.showPix !== false
    });
  } catch { /* ignore */ }
}

/* ================================================================= router */
function go(hash, replace) {
  if (location.hash === hash) route();
  else if (replace) history.replaceState(null, '', hash), route();
  else location.hash = hash;
}
function route() {
  closeSheet();
  const h = decodeURIComponent(location.hash.replace(/^#\/?/, ''));
  $('#btnSearch').classList.toggle('on', h.startsWith('search'));
  if (!h) {
    // A link arriving from someone else should explain itself before it
    // drops the reader into Greek.
    if (!seenWelcome()) { go('#/welcome', true); return; }
    go('#/' + S.book + '.' + S.ch, true); return;
  }
  if (h === 'welcome') { $('#ref').textContent = 'Welcome'; return welcomeView(); }
  if (h === 'chrono') { $('#ref').textContent = 'Chronology'; return chronoView(); }
  if (h === 'offline') { $('#ref').textContent = 'Offline'; return offlineView(); }
  if (h === 'about')  { $('#ref').textContent = 'About';      return aboutView(); }
  if (h === 'plates') { $('#ref').textContent = 'Engravings'; return platesView(); }
  if (h.startsWith('search')) {
    const q = (h.split('?q=')[1] || '').replace(/\+/g, ' ');
    $('#ref').textContent = 'Search';
    return runSearch(q, STAB);
  }
  const p = h.split('.');
  if (S.bookIx[p[0]]) return openChapter(p[0], +p[1] || 1, p[2] ? +p[2] : null);
  go('#/' + S.book + '.' + S.ch, true);
}

/* ========================================================= event wiring */
document.addEventListener('click', ev => {
  const t = ev.target.closest('[data-install],[data-look],[data-pan],[data-startreading],[data-listen],[data-aufrom],[data-setpix],[data-go2],[data-fs],[data-setscheme3],[data-settx],[data-setpron],[data-setscheme],[data-setscheme2],[data-tier],[data-dlstart],[data-dlstop],[data-dlclear],[data-cmf],[data-close],[data-v][data-t],[data-k],[data-ref],[data-conc],[data-dict],[data-book],[data-ch],[data-nav],[data-go],[data-tab],[data-expand]');
  if (!t) return;

  if (t.dataset.close) return closeSheet();

  if (t.dataset.expand != null) {
    const p = document.getElementById('def' + t.dataset.expand);
    if (p) { p.textContent = t.dataset.full; t.remove(); }
    return;
  }
  if (t.dataset.t != null && t.dataset.v != null && t.classList.contains('w')) {
    document.querySelectorAll('.w.sel').forEach(e => e.classList.remove('sel'));
    t.classList.add('sel');
    return void wordSheet(+t.dataset.v, +t.dataset.t);
  }
  if (t.dataset.fs) {
    S.fs = Math.min(FS_MAX, Math.max(FS_MIN, S.fs + (+t.dataset.fs) * FS_STEP));
    applyDisplay(); save(); displaySheet();
    return;
  }
  if (t.dataset.startreading) {
    markWelcome();
    return go('#/' + S.book + '.' + S.ch);
  }
  if (t.dataset.install) return void doInstall();
  if (t.dataset.look) return void lookAround(t.dataset.look);
  if (t.dataset.listen) return void listen(S.book, S.ch);
  if (t.dataset.aufrom !== undefined) {
    const el = auEl();
    if (el) { AU.seek = null; try { el.currentTime = 0; } catch {} el.play().catch(() => {}); }
    const e = document.getElementById('plEst');
    if (e) e.textContent = 'Started at the beginning of the recording.';
    return;
  }
  if (t.dataset.go2 === 'display') return displaySheet();
  if (t.dataset.settx)      { S.tx = t.dataset.settx; save(); renderChapter(); settingsSheet(); return; }
  if (t.dataset.setpron)    { S.pron = t.dataset.setpron; save(); settingsSheet(); return; }
  if (t.dataset.setscheme)  { S.chrono = t.dataset.setscheme; save(); settingsSheet(); return; }
  if (t.dataset.setscheme2) { S.chrono = t.dataset.setscheme2; save(); chronoView(); return; }
  if (t.dataset.setpix) {
    S.showPix = !S.showPix;
    save(); renderChapter(); displaySheet();
    return;
  }
  if (t.dataset.setscheme3) {
    S.scheme = t.dataset.setscheme3;
    applyDisplay(); save(); displaySheet();
    return;
  }
  if (t.dataset.tier) {
    const k = t.dataset.tier;
    S.dlTiers[k] = S.dlTiers[k] === false;
    return void offlineView();
  }
  if (t.dataset.dlstart) return void startDownload();
  if (t.dataset.dlstop)  { if (DL) DL.stop = true; return; }
  if (t.dataset.dlclear) return void clearDownloads();
  if (t.dataset.cmf) {
    CMF = t.dataset.cmf;
    return void (CMV == null ? cmChapterSheet() : cmSheet(CMV));
  }
  if (t.dataset.k === 'cmch') return void cmChapterSheet();
  if (t.dataset.k) {
    const vi = +t.dataset.v, i = +t.dataset.i;
    if (t.dataset.k === 'place')  return void placeSheet(vi, i);
    if (t.dataset.k === 'person') return void personSheet(vi, i);
    if (t.dataset.k === 'event')  return void eventSheet(vi, i);
    if (t.dataset.k === 'note')   return noteSheet(vi);
    if (t.dataset.k === 'xref')   return xrefSheet(vi);
    if (t.dataset.k === 'cm')     return void cmSheet(vi);
  }
  if (t.dataset.ref)   return go('#/' + t.dataset.ref);
  if (t.dataset.conc)  return void concSheet(t.dataset.conc);
  if (t.dataset.dict)  return void dictSheet(t.dataset.dict);
  if (t.dataset.book)  return chaptersSheet(t.dataset.book);
  if (t.dataset.ch)    return go('#/' + t.dataset.cbook + '.' + t.dataset.ch);
  if (t.dataset.nav)   return go('#/' + S.book + '.' + (S.ch + (t.dataset.nav === 'next' ? 1 : -1)));
  if (t.dataset.go)    return go('#/' + t.dataset.go);
  if (t.dataset.tab)   { STAB = t.dataset.tab; return void runSearch(SQ, STAB); }
});

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeSheet();
});
document.addEventListener('input', e => {
  if (e.target.id !== 'q') return;
  clearTimeout(window.__qt);
  const v = e.target.value;
  window.__qt = setTimeout(() => {
    history.replaceState(null, '', '#/search?q=' + encodeURIComponent(v).replace(/%20/g, '+'));
    const pos = e.target.selectionStart;
    runSearch(v, STAB).then(() => {
      const el = $('#q');
      if (el) { el.focus(); try { el.setSelectionRange(pos, pos); } catch {} }
    });
  }, 320);
});
document.addEventListener('submit', e => e.preventDefault());

/* =================================================================== boot */
async function boot() {
  load();
  applyDisplay();
  // Register before the first data fetch, not after. The worker claims this
  // page as soon as it activates, so registering late means the chapter you
  // are reading on your very first visit never reaches the cache — and
  // someone who loses signal right after opening the site is left with
  // nothing. Registering first closes that window.
  if ('serviceWorker' in navigator)
    navigator.serviceWorker.register('sw.js').catch(() => {});
  try {
    const [b, m, c, sc] = await Promise.all([
      get('books.json'), get('morph.json'), get('chronology.json'),
      get('schemes.json').catch(() => null)]);
    S.books = b.books; S.names = b.names; S.morph = m; S.chron = c;
    S.schemes = sc;
    S.books.forEach((x, i) => S.bookIx[x[0]] = { n: x[1], t: x[2], chapters: x[3], i });
    if (!(S.chron.schemes || []).some(s => s.scheme_id === S.chrono))
      S.chrono = (S.chron.schemes[0] || {}).scheme_id || 'jones';
  } catch (e) {
    $('#view').innerHTML = `<p class="load">The text would not load.
      If this is the first time you have opened it, you need to be online once;
      after that it works offline.<br><br><span class="ot">${esc(e.message)}</span></p>`;
    return;
  }
  $('#btnBooks').onclick = booksSheet;
  $('#btnSet').onclick = settingsSheet;
  $('#btnAa').onclick = displaySheet;
  $('#btnSearch').onclick = () => go('#/search?q=');
  $('#ref').onclick = () => chaptersSheet(S.book);
  $('#scrim').onclick = closeSheet;
  const plx = document.getElementById('plX');
  if (plx) plx.onclick = auStop;
  window.addEventListener('hashchange', route);
  route();
  warm();
}

/* Once the worker is in control, pull the chapter being read through it so
   it is in the cache. On a first visit the page is usually fetched before
   the worker is ready, so without this the current chapter is the one thing
   missing when the signal drops. */
async function warm() {
  if (!('serviceWorker' in navigator)) return;
  try {
    await navigator.serviceWorker.ready;
    if (!navigator.serviceWorker.controller) {
      await new Promise(res => {
        navigator.serviceWorker.addEventListener('controllerchange', res, { once: true });
        setTimeout(res, 4000);
      });
    }
    if (!navigator.serviceWorker.controller) return;
    const want = `${D}ch/${S.book}.${S.ch}.json`;
    fetch(want, { cache: 'no-store' }).catch(() => {});
  } catch { /* caching is a bonus, never a blocker */ }
}
boot();
