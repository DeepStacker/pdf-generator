/*
 * GSS-MIS service worker.
 *
 * Its one job is to make the app shell load instantly and survive a dropped
 * connection. It must never cache anything under /api/.
 *
 * That is not a performance preference. The server deletes an uploaded
 * workbook the moment its job ends and a generated report seconds after it is
 * served, and the run history no longer records who owned them. A cache entry
 * holding a downloaded report would put a copy of exactly that data back --
 * on the device, outside everything the server does to get rid of it, and
 * outliving all of it. So API traffic is passed straight through, and only
 * content-addressed build assets and the shell are ever stored.
 */

const CACHE = 'gss-mis-shell-v1';

// Hashed filenames change whenever their contents do, so a hit is always
// current and a miss just fetches. The shell itself is not content-addressed,
// which is why it is fetched fresh below whenever the network allows.
const isImmutableAsset = (url) =>
  url.pathname.startsWith('/assets/') ||
  url.pathname.startsWith('/icon-') ||
  url.pathname === '/logo.png' ||
  url.pathname === '/favicon.ico';

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.add('/')).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // Uploads, job state, downloads. Never stored, never served from a cache.
  if (url.pathname.startsWith('/api/')) return;

  if (isImmutableAsset(url)) {
    event.respondWith(
      caches.match(request).then((hit) =>
        hit || fetch(request).then((res) => {
          if (res.ok) {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(request, copy));
          }
          return res;
        })
      )
    );
    return;
  }

  // The shell: take the network's copy when there is one, so a deploy lands
  // on the next load rather than whenever the cache happens to turn over.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((res) => {
          if (res.ok) {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put('/', copy));
          }
          return res;
        })
        .catch(() => caches.match('/').then((hit) => hit || Response.error()))
    );
  }
});
