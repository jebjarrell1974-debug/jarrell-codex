/* Cache the shell up front; cache data files as they are read, so a chapter
   you have opened once opens again with no signal. */
/* BUILD is stamped by scripts/32_stamp_build.py from a digest of everything
   under data/. Any change to the text, the lexicons, the commentary or the
   indexes changes this string, which changes this file, which makes the
   browser fetch a new worker, which drops the stale data cache on activate.
   Without that, someone who opened the site once would keep the old data
   for ever. */
const BUILD = '4a3a18a2b932';
const SHELL = 'codex-shell-' + BUILD;
const DATA  = 'codex-data-' + BUILD;
const CORE  = ['./', 'index.html', 'app.css', 'scheme.css', 'app.js', 'icon.svg',
               'manifest.webmanifest',
               'font/spectral-400.woff2', 'font/spectral-600.woff2',
               'font/spectral-400i.woff2', 'font/hebrew-400.woff2',
               'font/hebrew-600.woff2', 'font/greek-400.woff2',
               'font/greek-600.woff2', 'font/greek-400i.woff2',
               'data/books.json', 'data/morph.json', 'data/chronology.json'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(SHELL)
    .then(c => c.addAll(CORE).catch(() => {}))
    .then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(ks => Promise.all(ks.filter(k => k !== SHELL && k !== DATA)
      .map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;

  const isData = url.pathname.includes('/data/');
  e.respondWith((async () => {
    const cache = await caches.open(isData ? DATA : SHELL);
    const hit = await cache.match(req, { ignoreSearch: true });
    if (hit) {
      if (!isData) fetch(req).then(r => r.ok && cache.put(req, r.clone())).catch(() => {});
      return hit;
    }
    try {
      const res = await fetch(req);
      if (res.ok) cache.put(req, res.clone());
      return res;
    } catch (err) {
      // Only a page navigation gets the shell back. Handing index.html to a
      // request for JSON makes the caller think it got data, and the reader
      // then reports an empty lexicon instead of saying it is offline.
      if (req.mode === 'navigate') {
        const shell = await caches.open(SHELL);
        const idx = await shell.match('index.html') || await shell.match('./');
        if (idx) return idx;
      }
      return new Response('Offline, and this file has not been downloaded yet.',
        { status: 504, headers: { 'Content-Type': 'text/plain' } });
    }
  })());
});
