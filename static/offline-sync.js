/**
 * Offline Sync Manager for CLAS PWA
 * 
 * Handles queuing of requests while offline and syncing when online.
 * Uses IndexedDB to persist pending requests.
 * 
 * Requirements: 4.3
 * Property 9: Offline Sync Capability
 */

class OfflineSyncManager {
  constructor() {
    this.dbName = 'CLAS_OfflineSync';
    this.storeName = 'pendingRequests';
    this.db = null;
    this.isOnline = navigator.onLine;
    
    this.init();
  }

  /**
   * Initialize the sync manager
   */
  async init() {
    try {
      // Open IndexedDB
      this.db = await this.openDatabase();
      
      // Listen for online/offline events
      window.addEventListener('online', () => this.handleOnline());
      window.addEventListener('offline', () => this.handleOffline());
      
      console.log('[Offline Sync] Manager initialized');
      
      // Try to sync any pending requests
      if (this.isOnline) {
        await this.syncPendingRequests();
      }
    } catch (error) {
      console.error('[Offline Sync] Initialization failed:', error);
    }
  }

  /**
   * Open or create IndexedDB database
   */
  openDatabase() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, 1);
      
      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(request.result);
      
      request.onupgradeneeded = (event) => {
        const db = event.target.result;
        
        // Create object store for pending requests
        if (!db.objectStoreNames.contains(this.storeName)) {
          const store = db.createObjectStore(this.storeName, { keyPath: 'id', autoIncrement: true });
          store.createIndex('timestamp', 'timestamp', { unique: false });
          store.createIndex('url', 'url', { unique: false });
        }
      };
    });
  }

  /**
   * Queue a request for later sync
   */
  async queueRequest(method, url, data = null, headers = {}) {
    try {
      if (!this.db) {
        console.warn('[Offline Sync] Database not initialized');
        return false;
      }

      const transaction = this.db.transaction([this.storeName], 'readwrite');
      const store = transaction.objectStore(this.storeName);
      
      const request = {
        method,
        url,
        data,
        headers,
        timestamp: Date.now(),
        retries: 0
      };
      
      return new Promise((resolve, reject) => {
        const addRequest = store.add(request);
        
        addRequest.onerror = () => {
          console.error('[Offline Sync] Failed to queue request:', addRequest.error);
          reject(addRequest.error);
        };
        
        addRequest.onsuccess = () => {
          console.log('[Offline Sync] Request queued:', url);
          resolve(true);
        };
      });
    } catch (error) {
      console.error('[Offline Sync] Queue request failed:', error);
      return false;
    }
  }

  /**
   * Get all pending requests
   */
  async getPendingRequests() {
    try {
      if (!this.db) return [];

      const transaction = this.db.transaction([this.storeName], 'readonly');
      const store = transaction.objectStore(this.storeName);
      
      return new Promise((resolve, reject) => {
        const request = store.getAll();
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);
      });
    } catch (error) {
      console.error('[Offline Sync] Get pending requests failed:', error);
      return [];
    }
  }

  /**
   * Remove a request from the queue
   */
  async removeRequest(id) {
    try {
      if (!this.db) return false;

      const transaction = this.db.transaction([this.storeName], 'readwrite');
      const store = transaction.objectStore(this.storeName);
      
      return new Promise((resolve, reject) => {
        const request = store.delete(id);
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
          console.log('[Offline Sync] Request removed:', id);
          resolve(true);
        };
      });
    } catch (error) {
      console.error('[Offline Sync] Remove request failed:', error);
      return false;
    }
  }

  /**
   * Sync all pending requests
   */
  async syncPendingRequests() {
    try {
      const pendingRequests = await this.getPendingRequests();
      
      if (pendingRequests.length === 0) {
        console.log('[Offline Sync] No pending requests to sync');
        return;
      }

      console.log(`[Offline Sync] Syncing ${pendingRequests.length} pending requests`);
      
      for (const request of pendingRequests) {
        try {
          const response = await fetch(request.url, {
            method: request.method,
            headers: {
              'Content-Type': 'application/json',
              ...request.headers
            },
            body: request.data ? JSON.stringify(request.data) : null
          });
          
          if (response.ok) {
            // Request succeeded, remove from queue
            await this.removeRequest(request.id);
            console.log('[Offline Sync] Request synced successfully:', request.url);
          } else {
            // Request failed, increment retry count
            console.warn('[Offline Sync] Request sync failed:', request.url, response.status);
          }
        } catch (error) {
          console.error('[Offline Sync] Request sync error:', request.url, error);
        }
      }
    } catch (error) {
      console.error('[Offline Sync] Sync pending requests failed:', error);
    }
  }

  /**
   * Handle online event
   */
  async handleOnline() {
    console.log('[Offline Sync] Device is online');
    this.isOnline = true;
    
    // Sync pending requests
    await this.syncPendingRequests();
    
    // Notify user
    this.notifyUser('Connection restored! Syncing data...', 'success');
  }

  /**
   * Handle offline event
   */
  handleOffline() {
    console.log('[Offline Sync] Device is offline');
    this.isOnline = false;
    
    // Notify user
    this.notifyUser('You are offline. Changes will be synced when online.', 'warning');
  }

  /**
   * Notify user of sync status
   */
  notifyUser(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `offline-sync-notification notification-${type}`;
    notification.textContent = message;
    
    // Add styles
    notification.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      padding: 12px 20px;
      border-radius: 4px;
      font-size: 14px;
      z-index: 9999;
      animation: slideIn 0.3s ease-out;
    `;
    
    // Set background color based on type
    const colors = {
      success: '#10b981',
      warning: '#f59e0b',
      error: '#ef4444',
      info: '#3b82f6'
    };
    
    notification.style.backgroundColor = colors[type] || colors.info;
    notification.style.color = 'white';
    
    document.body.appendChild(notification);
    
    // Remove after 4 seconds
    setTimeout(() => {
      notification.style.animation = 'slideOut 0.3s ease-out';
      setTimeout(() => notification.remove(), 300);
    }, 4000);
  }
}

// Initialize sync manager when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    window.offlineSyncManager = new OfflineSyncManager();
  });
} else {
  window.offlineSyncManager = new OfflineSyncManager();
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
  module.exports = OfflineSyncManager;
}
