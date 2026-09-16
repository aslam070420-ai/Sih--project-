const VERSION = '2f7f01e1eb8e32ea';
const CACHE = `farmdirect-final-${VERSION}`;
const BASE = new URL('./', self.location.href);
const OFFLINE = new URL(`static/offline.html?v=${VERSION}`, BASE).href;
const CORE = [
  'offline.html',
  'css/farmdirect-core.bundle.css',
  'css/visual_safe_perf.css',
  'js/farmdirect-core.bundle.js',
  'js/live-market.js',
  'vendor/bootstrap.min.css',
  'vendor/bootstrap.bundle.min.js',
  'vendor/bootstrap-icons.css',
  'icons/farmdirect-icon.svg'
].map(path => new URL(`static/${path}?v=${VERSION}`, BASE).href);
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(CORE)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k.startsWith('farmdirect-final-') && k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) return;
  if (event.request.mode === 'navigate') {
    event.respondWith(fetch(event.request).then(response => {
      if (response.ok) {
        const copy = response.clone();
        event.waitUntil(caches.open(CACHE).then(cache => cache.put(event.request, copy)));
      }
      return response;
    }).catch(async () => (await caches.match(event.request)) || caches.match(OFFLINE)));
    return;
  }
  if (url.pathname.startsWith(new URL('static/', BASE).pathname)) {
    event.respondWith(caches.match(event.request).then(cached => cached || fetch(event.request).then(response => {
      if (response.ok) {
        const copy = response.clone();
        event.waitUntil(caches.open(CACHE).then(cache => cache.put(event.request, copy)));
      }
      return response;
    })));
  }
});
