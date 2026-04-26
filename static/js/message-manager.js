/**
 * Message Management System for CLAS Application
 * Handles automatic dismissal and cleanup of Django messages
 */

class MessageManager {
    constructor() {
        this.init();
    }

    init() {
        // Initialize message system when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupMessages());
        } else {
            this.setupMessages();
        }
    }

    setupMessages() {
        // Clear any stale messages from previous sessions
        this.clearStaleMessages();
        
        // Setup auto-dismissal for current messages
        this.setupAutoDismissal();
        
        // Setup keyboard shortcuts
        this.setupKeyboardShortcuts();
        
        // Setup click handlers for manual dismissal
        this.setupClickHandlers();
    }

    clearStaleMessages() {
        // Check if this is a fresh page load (not a navigation within the same session)
        const isNewPageLoad = !sessionStorage.getItem('page_loaded');
        
        if (isNewPageLoad) {
            sessionStorage.setItem('page_loaded', 'true');
            
            // Clear success messages that might be stale from previous actions
            setTimeout(() => {
                const staleMessages = document.querySelectorAll('.alert-success, .alert-info');
                staleMessages.forEach(message => {
                    const text = message.textContent.toLowerCase();
                    
                    // Auto-clear common stale messages
                    if (text.includes('logged out') || 
                        text.includes('successfully') ||
                        text.includes('saved') ||
                        text.includes('updated') ||
                        text.includes('created') ||
                        text.includes('deleted')) {
                        
                        // Only clear if message seems old (no user interaction expected)
                        this.dismissMessage(message, 1500); // 1.5 second delay
                    }
                });
            }, 1000);
        }
    }

    setupAutoDismissal() {
        const messages = document.querySelectorAll('.alert');
        
        messages.forEach(message => {
            const messageType = this.getMessageType(message);
            const dismissTime = this.getDismissTime(messageType);
            
            if (dismissTime > 0) {
                setTimeout(() => {
                    this.dismissMessage(message);
                }, dismissTime);
            }
        });
    }

    getMessageType(message) {
        if (message.classList.contains('alert-success')) return 'success';
        if (message.classList.contains('alert-error')) return 'error';
        if (message.classList.contains('alert-warning')) return 'warning';
        if (message.classList.contains('alert-info')) return 'info';
        return 'default';
    }

    getDismissTime(messageType) {
        const dismissTimes = {
            'success': 3000,  // 3 seconds
            'info': 4000,     // 4 seconds
            'warning': 0,     // Manual dismissal only
            'error': 0,       // Manual dismissal only
            'default': 5000   // 5 seconds
        };
        
        return dismissTimes[messageType] || 5000;
    }

    dismissMessage(message, delay = 0) {
        if (!message || !message.parentElement) return;
        
        setTimeout(() => {
            if (message.parentElement) {
                // Add exit animation
                message.style.transition = 'all 0.3s ease-in-out';
                message.style.opacity = '0';
                message.style.transform = 'translateY(-10px)';
                
                // Remove from DOM after animation
                setTimeout(() => {
                    if (message.parentElement) {
                        message.remove();
                        this.checkEmptyContainer();
                    }
                }, 300);
            }
        }, delay);
    }

    checkEmptyContainer() {
        const container = document.getElementById('messagesContainer');
        if (container && container.children.length === 0) {
            container.style.display = 'none';
        }
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // ESC key dismisses all messages
            if (e.key === 'Escape') {
                const visibleMessages = document.querySelectorAll('.alert');
                visibleMessages.forEach(message => this.dismissMessage(message));
            }
        });
    }

    setupClickHandlers() {
        // Setup click handlers for close buttons
        document.addEventListener('click', (e) => {
            if (e.target.closest('.alert button')) {
                const message = e.target.closest('.alert');
                if (message) {
                    this.dismissMessage(message);
                }
            }
        });
    }

    // Public method to manually dismiss all messages
    dismissAll() {
        const messages = document.querySelectorAll('.alert');
        messages.forEach(message => this.dismissMessage(message));
    }

    // Public method to dismiss messages by type
    dismissByType(type) {
        const messages = document.querySelectorAll(`.alert-${type}`);
        messages.forEach(message => this.dismissMessage(message));
    }

    // Public method to add a new message programmatically
    addMessage(text, type = 'info', autoDismiss = true) {
        const container = document.getElementById('messagesContainer') || this.createMessageContainer();
        
        const messageElement = document.createElement('div');
        messageElement.className = `alert alert-${type} p-4 rounded-lg border-l-4 animate-fade-in ${this.getMessageClasses(type)}`;
        
        messageElement.innerHTML = `
            <div class="flex items-center">
                <span class="material-symbols-outlined mr-2 text-lg">
                    ${this.getMessageIcon(type)}
                </span>
                ${text}
                <button onclick="messageManager.dismissMessage(this.closest('.alert'))" class="ml-auto text-current opacity-50 hover:opacity-100" title="Dismiss">
                    <span class="material-symbols-outlined text-lg">close</span>
                </button>
            </div>
        `;
        
        container.appendChild(messageElement);
        container.style.display = 'block';
        
        if (autoDismiss) {
            const dismissTime = this.getDismissTime(type);
            if (dismissTime > 0) {
                setTimeout(() => this.dismissMessage(messageElement), dismissTime);
            }
        }
        
        return messageElement;
    }

    createMessageContainer() {
        const container = document.createElement('div');
        container.id = 'messagesContainer';
        container.className = 'mb-6 space-y-3';
        
        const mainContent = document.querySelector('main .flex-1');
        if (mainContent) {
            mainContent.insertBefore(container, mainContent.firstChild);
        }
        
        return container;
    }

    getMessageClasses(type) {
        const classes = {
            'error': 'bg-red-50 border-red-400 text-red-700',
            'warning': 'bg-yellow-50 border-yellow-400 text-yellow-700',
            'success': 'bg-green-50 border-green-400 text-green-700',
            'info': 'bg-blue-50 border-blue-400 text-blue-700'
        };
        
        return classes[type] || classes.info;
    }

    getMessageIcon(type) {
        const icons = {
            'error': 'error',
            'warning': 'warning',
            'success': 'check_circle',
            'info': 'info'
        };
        
        return icons[type] || icons.info;
    }
}

// Initialize message manager
const messageManager = new MessageManager();

// Make it globally available
window.messageManager = messageManager;

// Clean up session storage on page unload
window.addEventListener('beforeunload', () => {
    sessionStorage.removeItem('page_loaded');
});