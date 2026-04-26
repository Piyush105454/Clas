/**
 * Performance optimization utilities for CLAS application
 */

// Suppress console output in production
if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    console.log = console.warn = console.info = function() {};
}

class PerformanceOptimizer {
    constructor() {
        this.cache = new Map();
        this.requestQueue = new Map();
        this.observers = new Map();
        this.init();
    }

    init() {
        this.setupIntersectionObserver();
        this.setupRequestInterceptor();
        this.setupCacheManager();
        this.setupPreloader();
    }

    /**
     * Setup intersection observer for lazy loading
     */
    setupIntersectionObserver() {
        if ('IntersectionObserver' in window) {
            this.observers.set('lazy', new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        this.loadLazyContent(entry.target);
                        this.observers.get('lazy').unobserve(entry.target);
                    }
                });
            }, {
                threshold: 0.1,
                rootMargin: '50px'
            }));
        }
    }

    /**
     * Setup request interceptor for caching and deduplication
     */
    setupRequestInterceptor() {
        const originalFetch = window.fetch;
        window.fetch = async (url, options = {}) => {
            // Only cache and deduplicate GET requests
            const method = (options.method || 'GET').toUpperCase();
            if (method !== 'GET') {
                return originalFetch(url, options);
            }

            const cacheKey = this.getCacheKey(url, options);
            
            // Check cache first
            if (this.cache.has(cacheKey) && this.isCacheValid(cacheKey)) {
                return Promise.resolve(new Response(
                    JSON.stringify(this.cache.get(cacheKey).data),
                    { status: 200, headers: { 'Content-Type': 'application/json' } }
                ));
            }

            // Deduplicate concurrent requests
            if (this.requestQueue.has(cacheKey)) {
                return this.requestQueue.get(cacheKey);
            }

            // Make request
            const request = originalFetch(url, options)
                .then(response => {
                    if (response.ok && response.headers.get('content-type')?.includes('application/json')) {
                        return response.clone().json().then(data => {
                            this.cache.set(cacheKey, {
                                data,
                                timestamp: Date.now(),
                                ttl: this.getTTL(url)
                            });
                            return response;
                        });
                    }
                    return response;
                })
                .finally(() => {
                    this.requestQueue.delete(cacheKey);
                });

            this.requestQueue.set(cacheKey, request);
            return request;
        };
    }

    /**
     * Setup cache manager with automatic cleanup
     */
    setupCacheManager() {
        // Clean cache every 5 minutes
        setInterval(() => {
            this.cleanExpiredCache();
        }, 5 * 60 * 1000);
    }

    /**
     * Setup resource preloader
     */
    setupPreloader() {
        // Preload critical resources on idle
        if ('requestIdleCallback' in window) {
            requestIdleCallback(() => {
                this.preloadCriticalResources();
            });
        } else {
            setTimeout(() => {
                this.preloadCriticalResources();
            }, 1000);
        }
    }

    /**
     * Load lazy content for an element
     */
    loadLazyContent(element) {
        const loadType = element.dataset.lazyLoad;
        const url = element.dataset.lazyUrl;

        if (!url) return;

        switch (loadType) {
            case 'sessions':
                this.loadLazySessions(element, url);
                break;
            case 'schools':
                this.loadLazySchools(element, url);
                break;
            case 'stats':
                this.loadLazyStats(element, url);
                break;
            default:
                this.loadGenericContent(element, url);
        }
    }

    /**
     * Load sessions with pagination
     */
    async loadLazySessions(element, url) {
        try {
            element.innerHTML = this.getLoadingHTML();
            
            const response = await fetch(url);
            const data = await response.json();
            
            if (data.sessions) {
                element.innerHTML = this.renderSessions(data.sessions);
                
                // Setup pagination if needed
                if (data.pagination && data.pagination.has_next) {
                    this.setupPagination(element, data.pagination);
                }
            }
        } catch (error) {
            console.error('Error loading sessions:', error);
            element.innerHTML = this.getErrorHTML('Failed to load sessions');
        }
    }

    /**
     * Load schools with statistics
     */
    async loadLazySchools(element, url) {
        try {
            element.innerHTML = this.getLoadingHTML();
            
            const response = await fetch(url);
            const data = await response.json();
            
            if (data.schools) {
                element.innerHTML = this.renderSchools(data.schools);
            }
        } catch (error) {
            console.error('Error loading schools:', error);
            element.innerHTML = this.getErrorHTML('Failed to load schools');
        }
    }

    /**
     * Load dashboard statistics
     */
    async loadLazyStats(element, url) {
        try {
            const response = await fetch(url);
            const data = await response.json();
            
            this.updateStatsElements(data);
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }

    /**
     * Render sessions HTML
     */
    renderSessions(sessions) {
        return sessions.map(session => `
            <tr class="session-row hover:bg-gray-50" data-session-id="${session.id}">
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        Day ${session.day_number}
                    </span>
                </td>
                <td class="px-6 py-4">
                    <div class="text-sm font-medium text-gray-900">${session.title}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        ${session.status}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    ${session.created_by}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    ${session.updated_at}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div class="flex items-center justify-end gap-2">
                        <a href="${session.preview_url}" class="text-blue-600 hover:text-blue-900" title="Preview">
                            <span class="material-symbols-outlined text-lg">visibility</span>
                        </a>
                        <a href="${session.edit_url}" class="text-green-600 hover:text-green-900" title="Edit">
                            <span class="material-symbols-outlined text-lg">edit</span>
                        </a>
                        <a href="${session.delete_url}" class="text-red-600 hover:text-red-900" title="Delete">
                            <span class="material-symbols-outlined text-lg">delete</span>
                        </a>
                    </div>
                </td>
            </tr>
        `).join('');
    }

    /**
     * Render schools HTML
     */
    renderSchools(schools) {
        return schools.map(school => `
            <div class="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                <h3 class="font-semibold text-lg">${school.name}</h3>
                <p class="text-gray-600">${school.district}, ${school.state}</p>
                <div class="mt-2 flex gap-4 text-sm text-gray-500">
                    <span>Classes: ${school.total_classes}</span>
                    <span>Students: ${school.total_students}</span>
                    <span>Facilitators: ${school.active_facilitators}</span>
                </div>
                <div class="mt-3 flex gap-2">
                    <a href="${school.detail_url}" class="text-blue-600 hover:text-blue-800">View Details</a>
                    <a href="${school.edit_url}" class="text-green-600 hover:text-green-800">Edit</a>
                </div>
            </div>
        `).join('');
    }

    /**
     * Update statistics elements
     */
    updateStatsElements(data) {
        const statElements = {
            'hindiCount': data.hindi_sessions,
            'englishCount': data.english_sessions,
            'activeSchools': data.active_schools,
            'activeFacilitators': data.active_facilitators,
            'enrolledStudents': data.enrolled_students,
            'sessionsToday': data.sessions_today
        };

        Object.entries(statElements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element && value !== undefined) {
                this.animateNumber(element, parseInt(element.textContent) || 0, value);
            }
        });
    }

    /**
     * Animate number changes
     */
    animateNumber(element, from, to) {
        const duration = 1000;
        const steps = 60;
        const stepValue = (to - from) / steps;
        let current = from;
        let step = 0;

        const timer = setInterval(() => {
            current += stepValue;
            element.textContent = Math.round(current);
            
            if (++step >= steps) {
                element.textContent = to;
                clearInterval(timer);
            }
        }, duration / steps);
    }

    /**
     * Get loading HTML
     */
    getLoadingHTML() {
        return `
            <div class="flex items-center justify-center py-8">
                <div class="loading-spinner mr-3"></div>
                <span class="text-gray-600">Loading...</span>
            </div>
        `;
    }

    /**
     * Get error HTML
     */
    getErrorHTML(message) {
        return `
            <div class="text-center py-8">
                <div class="text-red-600 mb-2">⚠️ ${message}</div>
                <button onclick="location.reload()" class="text-blue-600 hover:text-blue-800">
                    Try Again
                </button>
            </div>
        `;
    }

    /**
     * Preload critical resources
     */
    preloadCriticalResources() {
        const criticalUrls = [
            '/api/dashboard/stats/',
            '/admin/curriculum-sessions/',
            '/admin/schools/'
        ];

        criticalUrls.forEach(url => {
            const link = document.createElement('link');
            link.rel = 'prefetch';
            link.href = url;
            document.head.appendChild(link);
        });
    }

    /**
     * Get cache key for request
     */
    getCacheKey(url, options) {
        return `${url}_${JSON.stringify(options)}`;
    }

    /**
     * Check if cache entry is valid
     */
    isCacheValid(cacheKey) {
        const entry = this.cache.get(cacheKey);
        if (!entry) return false;
        
        return Date.now() - entry.timestamp < entry.ttl;
    }

    /**
     * Get TTL for URL
     */
    getTTL(url) {
        if (url.includes('/api/dashboard/stats/')) return 5 * 60 * 1000; // 5 minutes
        if (url.includes('/api/lazy-load/')) return 10 * 60 * 1000; // 10 minutes
        return 5 * 60 * 1000; // Default 5 minutes
    }

    /**
     * Clean expired cache entries
     */
    cleanExpiredCache() {
        const now = Date.now();
        for (const [key, entry] of this.cache.entries()) {
            if (now - entry.timestamp > entry.ttl) {
                this.cache.delete(key);
            }
        }
    }

    /**
     * Observe element for lazy loading
     */
    observeElement(element) {
        if (this.observers.has('lazy')) {
            this.observers.get('lazy').observe(element);
        }
    }

    /**
     * Setup pagination for lazy loaded content
     */
    setupPagination(container, pagination) {
        if (pagination.has_next) {
            const loadMoreBtn = document.createElement('button');
            loadMoreBtn.className = 'w-full mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700';
            loadMoreBtn.textContent = 'Load More';
            loadMoreBtn.onclick = () => {
                const nextUrl = new URL(container.dataset.lazyUrl);
                nextUrl.searchParams.set('page', pagination.page + 1);
                this.loadLazyContent(container, nextUrl.toString());
            };
            container.appendChild(loadMoreBtn);
        }
    }
}

// Initialize performance optimizer when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.performanceOptimizer = new PerformanceOptimizer();
    
    // Observe all lazy load elements
    document.querySelectorAll('[data-lazy-load]').forEach(element => {
        window.performanceOptimizer.observeElement(element);
    });
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PerformanceOptimizer;
}