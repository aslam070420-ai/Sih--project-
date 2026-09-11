const CACHE = 'farmdirect-final-v16';
const CORE = [
  '/static/offline.html',
  '/static/css/style.css',
  '/static/css/cinematic.css',
  '/static/css/peak_v9.css',
  '/static/css/peak_v11.css',
  '/static/css/peak_v12.css',
  '/static/css/peak_v14.css',
  '/static/css/final.css',
  '/static/js/app.js',
  '/static/js/cinematic.js',
  '/static/js/site_motion.js',
  '/static/js/peak_v9.js',
  '/static/js/peak_v11.js',
  '/static/js/final.js',
  '/static/vendor/bootstrap.min.css',
  '/static/vendor/bootstrap.bundle.min.js',
  '/static/vendor/bootstrap-icons.css',
  '/static/icons/farmdirect-icon.svg'
];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(CORE)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) return;
  if (event.request.mode === 'navigate') {
    event.respondWith(fetch(event.request).then(response => {
      const copy = response.clone();
      caches.open(CACHE).then(cache => cache.put(event.request, copy));
      return response;
    }).catch(async () => (await caches.match(event.request)) || caches.match('/static/offline.html')));
    return;
  }
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(caches.match(event.request).then(cached => cached || fetch(event.request).then(response => {
      if (response.ok) caches.open(CACHE).then(cache => cache.put(event.request, response.clone()));
      return response;
    })));
  }
});
