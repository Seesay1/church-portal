const CACHE_NAME = 'church-cache-v1';
const urlsToCache = [
  '/',
  '/static/style.css',  // if you have a global CSS file
  '/static/script.js'    // if you have a global JS file
];

// Install event – cache files
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

// Fetch event – serve from cache, fallback to network
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request))
  );
});