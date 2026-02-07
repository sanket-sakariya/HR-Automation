/**
 * Audio Processing Web Worker
 * ==========================
 * Offloads heavy PCM conversion from main thread to maintain 60fps UI.
 * 
 * Features:
 * - Float32 to Int16 PCM conversion
 * - Volume/energy calculation
 * - dB level calculation for noise gate
 * - Consistent chunk timing (20ms intervals)
 */

// Configuration
const SEND_INTERVAL_MS = 20; // Send audio every 20ms for low latency
const VOLUME_THRESHOLD_DB = -35; // Below this dB level, audio is considered silence

// Buffer for accumulating samples between send intervals
let sampleBuffer = [];
let lastSendTime = 0;

/**
 * Convert Float32 samples to Int16 PCM
 * @param {Float32Array} float32Array - Input audio samples
 * @returns {Int16Array} - PCM encoded audio
 */
function float32ToInt16(float32Array) {
    const int16Array = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
        const s = Math.max(-1, Math.min(1, float32Array[i]));
        int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return int16Array;
}

/**
 * Calculate RMS energy from samples
 * @param {Float32Array|Int16Array} samples - Audio samples
 * @param {boolean} isFloat - Whether samples are float format
 * @returns {number} - RMS energy value
 */
function calculateEnergy(samples, isFloat = true) {
    let sumSquares = 0;
    const len = samples.length;
    
    for (let i = 0; i < len; i++) {
        const val = isFloat ? samples[i] : samples[i] / 32768.0;
        sumSquares += val * val;
    }
    
    return Math.sqrt(sumSquares / len);
}

/**
 * Convert RMS energy to dB level
 * @param {number} rms - RMS energy value
 * @returns {number} - dB level
 */
function rmsToDb(rms) {
    if (rms <= 0) return -Infinity;
    return 20 * Math.log10(rms);
}

/**
 * Calculate peak amplitude from samples
 * @param {Float32Array} samples - Audio samples
 * @returns {number} - Peak amplitude (0-1)
 */
function calculatePeak(samples) {
    let peak = 0;
    for (let i = 0; i < samples.length; i++) {
        const abs = Math.abs(samples[i]);
        if (abs > peak) peak = abs;
    }
    return peak;
}

/**
 * Process incoming audio data
 * - Accumulates samples
 * - Sends at consistent intervals
 * - Calculates volume metrics for noise gate
 */
function processAudioData(float32Data, timestamp) {
    // Add samples to buffer
    for (let i = 0; i < float32Data.length; i++) {
        sampleBuffer.push(float32Data[i]);
    }
    
    // Check if enough time has passed to send
    const now = timestamp || performance.now();
    const timeSinceLastSend = now - lastSendTime;
    
    if (timeSinceLastSend >= SEND_INTERVAL_MS && sampleBuffer.length > 0) {
        // Convert accumulated samples to Float32Array for processing
        const samples = new Float32Array(sampleBuffer);
        sampleBuffer = []; // Clear buffer
        lastSendTime = now;
        
        // Calculate volume metrics
        const rms = calculateEnergy(samples, true);
        const dbLevel = rmsToDb(rms);
        const peak = calculatePeak(samples);
        
        // Check if above noise threshold
        const isAboveThreshold = dbLevel > VOLUME_THRESHOLD_DB;
        
        // Convert to PCM
        const pcmData = float32ToInt16(samples);
        
        // Send processed data back to main thread
        self.postMessage({
            type: 'processed_audio',
            pcmBuffer: pcmData.buffer,
            metrics: {
                rms: rms,
                dbLevel: dbLevel,
                peak: peak,
                isAboveThreshold: isAboveThreshold,
                sampleCount: samples.length,
                timestamp: now
            }
        }, [pcmData.buffer]); // Transfer ownership for zero-copy
    }
}

/**
 * Force flush any remaining buffered samples
 */
function flushBuffer() {
    if (sampleBuffer.length > 0) {
        const samples = new Float32Array(sampleBuffer);
        sampleBuffer = [];
        
        const rms = calculateEnergy(samples, true);
        const dbLevel = rmsToDb(rms);
        const peak = calculatePeak(samples);
        const isAboveThreshold = dbLevel > VOLUME_THRESHOLD_DB;
        
        const pcmData = float32ToInt16(samples);
        
        self.postMessage({
            type: 'processed_audio',
            pcmBuffer: pcmData.buffer,
            metrics: {
                rms: rms,
                dbLevel: dbLevel,
                peak: peak,
                isAboveThreshold: isAboveThreshold,
                sampleCount: samples.length,
                timestamp: performance.now()
            }
        }, [pcmData.buffer]);
    }
}

/**
 * Reset worker state
 */
function reset() {
    sampleBuffer = [];
    lastSendTime = 0;
}

/**
 * Update configuration
 */
function updateConfig(config) {
    if (config.sendIntervalMs !== undefined) {
        console.log('Worker: sendIntervalMs update requested:', config.sendIntervalMs);
    }
    if (config.volumeThresholdDb !== undefined) {
        console.log('Worker: volumeThresholdDb update requested:', config.volumeThresholdDb);
    }
}

// Message handler
self.onmessage = function(event) {
    const { type, data, timestamp, config } = event.data;
    
    switch (type) {
        case 'audio_data':
            // Process incoming audio samples
            processAudioData(new Float32Array(data), timestamp);
            break;
            
        case 'flush':
            // Force send any remaining buffered data
            flushBuffer();
            break;
            
        case 'reset':
            // Clear all state
            reset();
            break;
            
        case 'config':
            // Update worker configuration
            updateConfig(config);
            break;
            
        default:
            console.warn('Worker: Unknown message type:', type);
    }
};

// Signal ready state
self.postMessage({ type: 'ready' });
