// Service Worker for ส.ก. Navigator PWA
// Version: sk-navigator-v7 (2026-04-11 — CSS restoration + force reload)

const CACHE_NAME = 'sk-navigator-v7';

const URLS_TO_CACHE = [
  './',
  './index.html',
  './campaign-tracker.html',
  './campaign-dashboard.html',
  './district-intel.html',
  './phase-a.html',
  './phase-b.html',
  './phase-c.html',
  './phase-d-e.html',
  './sk-candidate-guide.html',
  './election_expenses_data.js',
  './manifest.json'
];

const GOOGLE_FONTS_CACHE = 'sk-fonts-v1';

// Install — pre-cache main pages
self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function(cache) {
      // Use addAll but allow individual failures to not block whole install
      return Promise.all(
        URLS_TO_CACHE.map(function(url) {
          return cache.add(url).catch(function(err) {
            console.warn('[SW] Failed to cache:', url, err);
          });
        })
      );
    })
  );
  self.skipWaiting();
});

// Activate — clean up old caches
self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.filter(function(name) {
          return name !== CACHE_NAME && name !== GOOGLE_FONTS_CACHE;
        }).map(function(name) {
          return caches.delete(name);
        })
      );
    })
  );
  self.clients.claim();
});

// Fetch — strategy per request type
self.addEventListener('fetch', function(event) {
  var url = event.request.url;

  // Network first for API calls (Traffy Fondue, etc.)
  if (url.includes('api.') || url.includes('traffy') || url.includes('fondue')) {
    event.respondWith(
      fetch(event.request).catch(function() {
        return caches.match(event.request);
      })
    );
    return;
  }

  // Cache first for Google Fonts
  if (url.includes('fonts.googleapis.com') || url.includes('fonts.gstatic.com')) {
    event.respondWith(
      caches.open(GOOGLE_FONTS_CACHE).then(function(cache) {
        return cache.match(event.request).then(function(cached) {
          if (cached) return cached;
          return fetch(event.request).then(function(response) {
            cache.put(event.request, response.clone());
            return response;
          });
        });
      })
    );
    return;
  }

  // HTML pages: network first (always get latest), cache fallback for offline
  if (event.request.headers.get('accept') && event.request.headers.get('accept').includes('text/html')) {
    event.respondWith(
      fetch(event.request).then(function(response) {
        return caches.open(CACHE_NAME).then(function(cache) {
          cache.put(event.request, response.clone());
          return response;
        });
      }).catch(function() {
        return caches.match(event.request);
      })
    );
    return;
  }

  // Other assets: cache first, network fallback
  event.respondWith(
    caches.match(event.request).then(function(cached) {
      return cached || fetch(event.request);
    })
  );
});
