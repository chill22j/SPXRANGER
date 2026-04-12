const CACHE = 'pvi-v4';
const ASSETS = ['/', '/index.html', '/manifest.json', '/data/market.json'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
  ).then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  const url = e.request.url;

  // data/market.json: network first, fall back to cache
  if (url.includes('market.json')) {
    e.respondWith(
      fetch(e.request).then(res => {
        const clone = res.clone();
        caches.open(CACHE).then(c => c.put(e.request, clone));
        return res;
      }).catch(() => caches.match(e.request))
    );
    return;
  }

  // Yahoo Finance (live fetch): network only, no cache
  if (url.includes('yahoo.com') || url.includes('finance.yahoo')) {
    e.respondWith(fetch(e.request));
    return;
  }

  // Everything else: cache first
  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request))
  );
});
