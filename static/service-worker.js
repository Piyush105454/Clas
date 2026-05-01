/**
 * Service Worker for CLAS PWA
 * 
 * Handles caching, offline support, and background sync
 * Requirements: 1.2, 1.3, 1.4, 1.5, 3.2, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.4
 */

// Cache names with versions for cache invalidation
// ✅ PRODUCTION FIX: Increment version number whenever UI changes
// This forces browsers to download new cache
const CACHE_NAMES = {
  static: 'static-v12',
  pages: 'pages-v12',
  api: 'api-v12',
  offline: 'offline-v12'
};

// Critical assets to cache on install
const CRITICAL_ASSETS = [
  '/',
  '/offline/'
];

// Asset patterns for routing
const ASSET_PATTERNS = {
  static: /\.(css|js|png|jpg|jpeg|gif|svg|woff|woff2|ttf|eot)$/i,
  pages: /\.html$|\/$/,
  api: /\/api\//
};


/**
 * Install Event - Cache critical assets
 * Property 2: Service Worker Registration
 * Property 3: Static Asset Caching
 */
self.addEventListener('install', (event) => {
  console.log('[Service Worker] Installing...');
  
  event.waitUntil(
    caches.open(CACHE_NAMES.static)
      .then((cache) => {
        console.log('[Service Worker] Caching critical assets');
        return cache.addAll(CRITICAL_ASSETS);
      })
      .then(() => {
        console.log('[Service Worker] Installation complete');
        return self.skipWaiting();
      })
      .catch((error) => {
        console.error('[Service Worker] Installation failed:', error);
      })
  );
});

/**
 * Activate Event - Clean up old caches
 * Property 6: Cache Versioning
 * Property 7: Service Worker Update Detection
 */
self.addEventListener('activate', (event) => {
  console.log('[Service Worker] Activating...');
  
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            // Delete ALL old cache versions to force refresh
            console.log('[Service Worker] Deleting cache:', cacheName);
            return caches.delete(cacheName);
          })
        );
      })
      .then(() => {
        console.log('[Service Worker] Activation complete - all caches cleared');
        return self.clients.claim();
      })
      .then(() => {
        // Notify all clients to reload
        return self.clients.matchAll();
      })
      .then((clients) => {
        clients.forEach((client) => {
          client.postMessage({
            type: 'CACHE_UPDATED',
            message: 'Service worker updated. Please refresh the page.'
          });
        });
      })
      .catch((error) => {
        console.error('[Service Worker] Activation failed:', error);
      })
  );
});

/**
 * Fetch Event - Intercept requests and apply caching strategies
 * Property 3: Static Asset Caching
 * Property 4: Offline Page Serving
 * Property 5: Offline Fallback
 * Property 8: Network-First Strategy for Pages
 * Property 10: Critical Asset Prioritization
 */
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip chrome extensions and other non-http(s) requests
  if (!url.protocol.startsWith('http')) {
    return;
  }

  // Determine caching strategy based on request type
  if (isStaticAsset(url)) {
    // Cache-first strategy for static assets
    event.respondWith(cacheFirstStrategy(request));
  } else if (isPageRequest(url)) {
    // Network-first strategy for HTML pages
    event.respondWith(networkFirstStrategy(request));
  } else if (isApiRequest(url)) {
    // Network-first strategy for API requests
    event.respondWith(networkFirstStrategy(request));
  }
});

/**
 * Cache-first strategy: Check cache first, fall back to network
 * Used for: CSS, JavaScript, images, fonts
 * Property 3: Static Asset Caching
 */
function cacheFirstStrategy(request) {
  return caches.match(request)
    .then((response) => {
      if (response) {
        console.log('[Service Worker] Serving from cache:', request.url);
        return response;
      }

      // Not in cache, fetch from network
      return fetch(request)
        .then((response) => {
          // Don't cache non-successful responses
          if (!response || response.status !== 200 || response.type === 'error') {
            return response;
          }

          // Clone the response
          const responseToCache = response.clone();

          // Cache the response
          caches.open(CACHE_NAMES.static)
            .then((cache) => {
              cache.put(request, responseToCache);
            })
            .catch((error) => {
              console.error('[Service Worker] Cache put failed:', error);
            });

          return response;
        })
        .catch((error) => {
          console.error('[Service Worker] Fetch failed:', error);
          // Return offline fallback for pages
          if (isPageRequest(new URL(request.url))) {
            return caches.match('/offline/');
          }
          throw error;
        });
    });
}

/**
 * Network-first strategy: Try network first, fall back to cache
 * Used for: HTML pages, API responses
 * Property 4: Offline Page Serving
 * Property 5: Offline Fallback
 * Property 8: Network-First Strategy for Pages
 */
function networkFirstStrategy(request) {
  return fetch(request)
    .then((response) => {
      // Don't cache non-successful responses
      if (!response || response.status !== 200) {
        return response;
      }

      // Clone the response
      const responseToCache = response.clone();

      // Determine which cache to use
      const cacheName = isApiRequest(new URL(request.url)) 
        ? CACHE_NAMES.api 
        : CACHE_NAMES.pages;

      // Cache the response
      caches.open(cacheName)
        .then((cache) => {
          cache.put(request, responseToCache);
        })
        .catch((error) => {
          console.error('[Service Worker] Cache put failed:', error);
        });

      return response;
    })
    .catch((error) => {
      console.error('[Service Worker] Network request failed:', error);

      // Try to return cached response
      return caches.match(request)
        .then((response) => {
          if (response) {
            console.log('[Service Worker] Serving cached response:', request.url);
            return response;
          }

          // No cached response, return offline fallback
          console.log('[Service Worker] Serving offline fallback:', request.url);
          return caches.match('/offline/');
        })
        .catch((cacheError) => {
          console.error('[Service Worker] Cache match failed:', cacheError);
          // Last resort: return offline page
          return caches.match('/offline/');
        });
    });
}

/**
 * Check if request is for a static asset
 * Property 3: Static Asset Caching
 */
function isStaticAsset(url) {
  return ASSET_PATTERNS.static.test(url.pathname);
}

/**
 * Check if request is for an HTML page
 * Property 4: Offline Page Serving
 */
function isPageRequest(url) {
  // Check if it's an HTML file or a route (ends with / or no extension)
  const pathname = url.pathname;
  return pathname.endsWith('.html') || 
         pathname.endsWith('/') || 
         (!pathname.includes('.') && !pathname.startsWith('/api'));
}

/**
 * Check if request is for an API endpoint
 * Property 8: Network-First Strategy for Pages
 */
function isApiRequest(url) {
  return ASSET_PATTERNS.api.test(url.pathname);
}

/**
 * Message handler for cache management
 * Property 6: Cache Versioning
 */
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (event.data && event.data.type === 'CLEAR_CACHE') {
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => caches.delete(cacheName))
      );
    });
  }
});
