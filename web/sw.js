/* Cache the shell up front; cache data files as they are read, so a chapter
   you have opened once opens again with no signal. */
const SHELL = 'codex-shell-v2';
const DATA  = 'codex-data-v1';
const CORE  = ['./', 'index.html', 'app.css', 'app.js', 'icon.svg',
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
      const shell = await caches.open(SHELL);
      return (await shell.match('index.html')) ||
        new Response('Offline and not cached yet.', { status: 503 });
    }
  })());
});
