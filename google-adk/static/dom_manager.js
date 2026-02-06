/**
 * DOM Manager - Memory-Efficient Transcript Management
 * ====================================================
 * Implements a capped list to prevent DOM bloat and browser slowdown.
 * 
 * Features:
 * - Maximum transcript entries limit (default: 50)
 * - Automatic cleanup of oldest entries
 * - Memory usage tracking
 * - Smooth removal animations
 * - Audio source cleanup tracking
 */

class DOMManager {
    /**
     * @param {Object} config - Configuration options
     * @param {number} config.maxTranscriptEntries - Maximum transcript entries before cleanup
     * @param {HTMLElement} config.transcriptContainer - Container element for transcripts
     * @param {Function} config.onCleanup - Callback when entries are cleaned up
     */
    constructor(config = {}) {
        this.maxEntries = config.maxTranscriptEntries || 50;
        this.container = config.transcriptContainer || null;
        this.onCleanup = config.onCleanup || null;
        
        // Track entries for efficient management
        this.entries = [];
        this.entryCount = 0;
        
        // Memory tracking
        this.memoryStatus = 'stable';
        this.lastCleanupTime = Date.now();
        this.cleanupCount = 0;
        
        // Audio source tracking for cleanup
        this.audioSources = new Set();
        
        // Performance monitoring
        this.performanceMetrics = {
            avgRenderTime: 0,
            cleanupTimes: [],
            domOperations: 0
        };
    }
    
    /**
     * Set the transcript container element
     * @param {HTMLElement} container - The container element
     */
    setContainer(container) {
        this.container = container;
    }
    
    /**
     * Add a new transcript entry with automatic cleanup
     * @param {HTMLElement} element - The element to add
     * @param {string} type - Entry type ('interviewer' or 'candidate')
     * @returns {HTMLElement} - The added element
     */
    addEntry(element, type = 'message') {
        if (!this.container) {
            console.warn('DOMManager: No container set');
            return element;
        }
        
        const startTime = performance.now();
        
        // Track the entry
        this.entries.push({
            element: element,
            type: type,
            timestamp: Date.now(),
            id: ++this.entryCount
        });
        
        // Add to DOM
        this.container.appendChild(element);
        this.performanceMetrics.domOperations++;
        
        // Check if cleanup needed
        if (this.entries.length > this.maxEntries) {
            this.cleanupOldEntries();
        }
        
        // Track render time
        const renderTime = performance.now() - startTime;
        this.updateRenderTimeMetric(renderTime);
        
        return element;
    }
    
    /**
     * Remove oldest entries to maintain memory efficiency
     * @param {number} count - Number of entries to remove (default: 10)
     */
    cleanupOldEntries(count = 10) {
        const startTime = performance.now();
        const toRemove = Math.min(count, this.entries.length - this.maxEntries + count);
        
        if (toRemove <= 0) return;
        
        // Remove oldest entries
        for (let i = 0; i < toRemove; i++) {
            const entry = this.entries.shift();
            if (entry && entry.element && entry.element.parentNode) {
                // Add fade-out animation
                entry.element.style.transition = 'opacity 0.2s ease, transform 0.2s ease';
                entry.element.style.opacity = '0';
                entry.element.style.transform = 'translateX(-20px)';
                
                // Remove after animation
                setTimeout(() => {
                    if (entry.element.parentNode) {
                        entry.element.parentNode.removeChild(entry.element);
                    }
                }, 200);
            }
        }
        
        // Track cleanup metrics
        const cleanupTime = performance.now() - startTime;
        this.performanceMetrics.cleanupTimes.push(cleanupTime);
        if (this.performanceMetrics.cleanupTimes.length > 10) {
            this.performanceMetrics.cleanupTimes.shift();
        }
        
        this.cleanupCount++;
        this.lastCleanupTime = Date.now();
        
        // Callback
        if (this.onCleanup) {
            this.onCleanup({
                removed: toRemove,
                remaining: this.entries.length,
                cleanupTime: cleanupTime
            });
        }
        
        console.log(`DOMManager: Cleaned up ${toRemove} entries, ${this.entries.length} remaining`);
    }
    
    /**
     * Clear all transcript entries
     */
    clearAll() {
        if (!this.container) return;
        
        // Remove all tracked entries
        this.entries.forEach(entry => {
            if (entry.element && entry.element.parentNode) {
                entry.element.parentNode.removeChild(entry.element);
            }
        });
        
        this.entries = [];
        this.performanceMetrics.domOperations++;
    }
    
    /**
     * Register an AudioBufferSourceNode for cleanup tracking
     * @param {AudioBufferSourceNode} source - The audio source to track
     */
    registerAudioSource(source) {
        this.audioSources.add(source);
        
        // Auto-cleanup when source ends
        source.onended = () => {
            this.cleanupAudioSource(source);
        };
    }
    
    /**
     * Cleanup a specific audio source
     * @param {AudioBufferSourceNode} source - The audio source to cleanup
     */
    cleanupAudioSource(source) {
        if (!source) return;
        
        try {
            source.disconnect();
            source.buffer = null;
            source.onended = null;
        } catch (e) {
            // Source may already be cleaned up
        }
        
        this.audioSources.delete(source);
    }
    
    /**
     * Cleanup all registered audio sources
     */
    cleanupAllAudioSources() {
        this.audioSources.forEach(source => {
            this.cleanupAudioSource(source);
        });
        this.audioSources.clear();
    }
    
    /**
     * Update average render time metric
     * @param {number} renderTime - Time taken to render in ms
     */
    updateRenderTimeMetric(renderTime) {
        const alpha = 0.2; // Smoothing factor
        this.performanceMetrics.avgRenderTime = 
            alpha * renderTime + (1 - alpha) * this.performanceMetrics.avgRenderTime;
    }
    
    /**
     * Get current memory status
     * @returns {Object} - Memory status information
     */
    getMemoryStatus() {
        // Check if performance.memory is available (Chrome only)
        let heapUsed = null;
        let heapLimit = null;
        
        if (performance.memory) {
            heapUsed = performance.memory.usedJSHeapSize;
            heapLimit = performance.memory.jsHeapSizeLimit;
        }
        
        // Determine status based on metrics
        if (this.performanceMetrics.avgRenderTime > 100) {
            this.memoryStatus = 'degraded';
        } else if (this.entries.length > this.maxEntries * 0.9) {
            this.memoryStatus = 'warning';
        } else {
            this.memoryStatus = 'stable';
        }
        
        return {
            status: this.memoryStatus,
            entryCount: this.entries.length,
            maxEntries: this.maxEntries,
            avgRenderTime: Math.round(this.performanceMetrics.avgRenderTime * 100) / 100,
            cleanupCount: this.cleanupCount,
            audioSourcesTracked: this.audioSources.size,
            heapUsed: heapUsed,
            heapLimit: heapLimit,
            domOperations: this.performanceMetrics.domOperations
        };
    }
    
    /**
     * Get entries count
     * @returns {number} - Current number of entries
     */
    getEntryCount() {
        return this.entries.length;
    }
    
    /**
     * Force garbage collection hint (not guaranteed)
     */
    suggestGC() {
        // Clear any temporary references
        if (this.performanceMetrics.cleanupTimes.length > 5) {
            this.performanceMetrics.cleanupTimes = 
                this.performanceMetrics.cleanupTimes.slice(-5);
        }
        
        // Note: We can't force GC, but we can help by nullifying references
        console.log('DOMManager: GC suggestion made');
    }
    
    /**
     * Destroy the manager and cleanup all resources
     */
    destroy() {
        this.clearAll();
        this.cleanupAllAudioSources();
        this.container = null;
        this.onCleanup = null;
        this.entries = [];
        this.performanceMetrics = null;
    }
}

// Export for use in modules or attach to window for global access
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DOMManager;
} else {
    window.DOMManager = DOMManager;
}
