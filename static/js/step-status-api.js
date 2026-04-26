/**
 * Step Status API Helper
 * Provides functions to save and load step completion status from the database
 * Replaces localStorage-based step tracking with persistent database storage
 */

class StepStatusAPI {
    constructor() {
        this.baseUrl = '/api/step-status';
        this.cache = {};
    }

    /**
     * Save step completion status to database
     * @param {string} plannedSessionId - UUID of the planned session
     * @param {string} sessionDate - Date in YYYY-MM-DD format
     * @param {number} stepNumber - Step number (1-7)
     * @param {boolean} isCompleted - Whether step is completed
     * @param {object} stepContent - Optional JSON data for the step
     * @returns {Promise<object>} Response from server
     */
    async saveStepStatus(plannedSessionId, sessionDate, stepNumber, isCompleted, stepContent = {}) {
        try {
            const response = await fetch(`${this.baseUrl}/save/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken(),
                },
                body: JSON.stringify({
                    planned_session_id: plannedSessionId,
                    session_date: sessionDate,
                    step_number: stepNumber,
                    is_completed: isCompleted,
                    step_content: stepContent,
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            if (data.success) {
                console.log(`✅ Step ${stepNumber} status saved to database`);
                // Invalidate cache
                this.invalidateCache(plannedSessionId, sessionDate);
            } else {
                console.error(`❌ Error saving step status: ${data.error}`);
            }
            
            return data;
        } catch (error) {
            console.error('Error saving step status:', error);
            throw error;
        }
    }

    /**
     * Get all step statuses for a session
     * @param {string} plannedSessionId - UUID of the planned session
     * @param {string} sessionDate - Date in YYYY-MM-DD format
     * @returns {Promise<object>} Object with step statuses keyed by step number
     */
    async getStepStatuses(plannedSessionId, sessionDate) {
        try {
            // Check cache first
            const cacheKey = `${plannedSessionId}:${sessionDate}`;
            if (this.cache[cacheKey]) {
                console.log('📦 Using cached step statuses');
                return this.cache[cacheKey];
            }

            const response = await fetch(
                `${this.baseUrl}/get/?planned_session_id=${plannedSessionId}&session_date=${sessionDate}`,
                {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                }
            );

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            if (data.success) {
                console.log(`✅ Retrieved step statuses from database`);
                // Cache the result
                this.cache[cacheKey] = data.steps;
                return data.steps;
            } else {
                console.error(`❌ Error retrieving step statuses: ${data.error}`);
                return null;
            }
        } catch (error) {
            console.error('Error retrieving step statuses:', error);
            throw error;
        }
    }

    /**
     * Check if a specific step is completed
     * @param {string} plannedSessionId - UUID of the planned session
     * @param {string} sessionDate - Date in YYYY-MM-DD format
     * @param {number} stepNumber - Step number (1-7)
     * @returns {Promise<boolean>} Whether the step is completed
     */
    async isStepCompleted(plannedSessionId, sessionDate, stepNumber) {
        try {
            const steps = await this.getStepStatuses(plannedSessionId, sessionDate);
            if (steps && steps[stepNumber]) {
                return steps[stepNumber].is_completed;
            }
            return false;
        } catch (error) {
            console.error('Error checking step completion:', error);
            return false;
        }
    }

    /**
     * Mark a step as completed
     * @param {string} plannedSessionId - UUID of the planned session
     * @param {string} sessionDate - Date in YYYY-MM-DD format
     * @param {number} stepNumber - Step number (1-7)
     * @param {object} stepContent - Optional JSON data for the step
     * @returns {Promise<object>} Response from server
     */
    async markStepCompleted(plannedSessionId, sessionDate, stepNumber, stepContent = {}) {
        return this.saveStepStatus(plannedSessionId, sessionDate, stepNumber, true, stepContent);
    }

    /**
     * Mark a step as incomplete
     * @param {string} plannedSessionId - UUID of the planned session
     * @param {string} sessionDate - Date in YYYY-MM-DD format
     * @param {number} stepNumber - Step number (1-7)
     * @returns {Promise<object>} Response from server
     */
    async markStepIncomplete(plannedSessionId, sessionDate, stepNumber) {
        return this.saveStepStatus(plannedSessionId, sessionDate, stepNumber, false, {});
    }

    /**
     * Clear (mark as incomplete) a specific step or all steps
     * @param {string} plannedSessionId - UUID of the planned session
     * @param {string} sessionDate - Date in YYYY-MM-DD format
     * @param {number} stepNumber - Optional step number (1-7). If not provided, clears all steps
     * @returns {Promise<object>} Response from server
     */
    async clearStepStatus(plannedSessionId, sessionDate, stepNumber = null) {
        try {
            const body = {
                planned_session_id: plannedSessionId,
                session_date: sessionDate,
            };
            
            if (stepNumber) {
                body.step_number = stepNumber;
            }

            const response = await fetch(`${this.baseUrl}/clear/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken(),
                },
                body: JSON.stringify(body),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            if (data.success) {
                console.log(`✅ Step status cleared`);
                // Invalidate cache
                this.invalidateCache(plannedSessionId, sessionDate);
            } else {
                console.error(`❌ Error clearing step status: ${data.error}`);
            }
            
            return data;
        } catch (error) {
            console.error('Error clearing step status:', error);
            throw error;
        }
    }

    /**
     * Get CSRF token from cookie
     * @returns {string} CSRF token
     */
    getCsrfToken() {
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    /**
     * Invalidate cache for a session
     * @param {string} plannedSessionId - UUID of the planned session
     * @param {string} sessionDate - Date in YYYY-MM-DD format
     */
    invalidateCache(plannedSessionId, sessionDate) {
        const cacheKey = `${plannedSessionId}:${sessionDate}`;
        delete this.cache[cacheKey];
        console.log('🗑️ Cache invalidated');
    }

    /**
     * Clear all cache
     */
    clearCache() {
        this.cache = {};
        console.log('🗑️ All cache cleared');
    }
}

// Create global instance
const stepStatusAPI = new StepStatusAPI();
