/**
 * Resource Prioritization for CLAS PWA
 * Prioritizes loading of critical assets based on network speed
 */

class ResourcePrioritizer {
  constructor() {
    this.init();
  }

  init() {
    this.monitorNetworkSpeed();
    console.log('[Resource Prioritization] Initialized');
  }

  monitorNetworkSpeed() {
    if ('connection' in navigator) {
      const connection = navigator.connection;
      const effectiveType = connection.effectiveType;
      console.log('[Resource Prioritization] Network type:', effectiveType);
      
      if (effectiveType === '4g') {
        this.setLoadingStrategy('fast');
      } else if (effectiveType === '3g') {
        this.setLoadingStrategy('moderate');
      } else {
        this.setLoadingStrategy('slow');
      }
      
      connection.addEventListener('change', () => {
        const newType = connection.effectiveType;
        console.log('[Resource Prioritization] Network type changed:', newType);
        this.setLoadingStrategy(newType === '4g' ? 'fast' : newType === '3g' ? 'moderate' : 'slow');
      });
    }
  }

  setLoadingStrategy(speed) {
    const strategy = {
      fast: {
        imageQuality: 'high',
        preloadImages: true,
        lazyLoadThreshold: 1000
      },
      moderate: {
        imageQuality: 'medium',
        preloadImages: false,
        lazyLoadThreshold: 500
      },
      slow: {
        imageQuality: 'low',
        preloadImages: false,
        lazyLoadThreshold: 100
      }
    };
    
    const config = strategy[speed] || strategy.moderate;
    window.resourceStrategy = config;
    this.applyLazyLoading(config.lazyLoadThreshold);
    console.log('[Resource Prioritization] Loading strategy set:', speed, config);
  }

  applyLazyLoading(threshold) {
    if ('IntersectionObserver' in window) {
      const images = document.querySelectorAll('img[data-src]');
      
      const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const img = entry.target;
            img.src = img.dataset.src;
            img.removeAttribute('data-src');
            observer.unobserve(img);
          }
        });
      }, {
        rootMargin: `${threshold}px`
      });
      
      images.forEach(img => imageObserver.observe(img));
    }
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    window.resourcePrioritizer = new ResourcePrioritizer();
  });
} else {
  window.resourcePrioritizer = new ResourcePrioritizer();
}
