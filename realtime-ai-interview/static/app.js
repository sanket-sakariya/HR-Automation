/**
 * Real-time Multilingual AI Interviewer - Professional Grade Audio
 * 
 * ARCHITECTURE:
 * =============
 * Model: gemini-2.5-flash-native-audio-preview-12-2025
 * 
 * AUDIO PIPELINE:
 * ===============
 * INPUT (User → Gemini):
 *   Browser Mic (44.1kHz/48kHz Float32) → Linear Interpolation Resampler → 16kHz Int16 → Base64 → WebSocket
 * 
 * OUTPUT (Gemini → User):
 *   WebSocket → Base64 → 24kHz Int16 → Linear Interpolation Resampler → Browser Rate → Jitter Buffer → Speaker
 * 
 * KEY FEATURES:
 * - Precision Linear Interpolation Resampling (both directions)
 * - 50-100ms Jitter Buffer for gapless playback
 * - Proper barge-in with audioContext.suspend() and queue clearing
 * - Zero server-side audio processing (transparent proxy)
 */

// ============== Configuration ==============
const GEMINI_INPUT_RATE = 16000;      // What Gemini expects from us
const GEMINI_OUTPUT_RATE = 24000;     // What Gemini sends to us
const JITTER_BUFFER_MS = 100;         // 100ms look-ahead buffer for smooth playback
const INITIAL_BUFFER_CHUNKS = 3;      // Wait for 3 chunks before starting playback (prevents fast start)
const SAFETY_MARGIN_MS = 50;          // Safety margin when resetting playback
const INPUT_CHUNK_INTERVAL_MS = 100;  // Send input chunks every 100ms (rate limiting)
const OUTPUT_PROCESS_INTERVAL_MS = 20; // Process output queue every 20ms (rate limiting output)
const NUM_VISUALIZER_BARS = 32;

// ============== State ==============
let websocket = null;
let audioStreamer = null;            // Professional AudioStreamer instance
let audioRecorder = null;            // Professional AudioRecorder instance
let isInterviewActive = false;
let isAISpeaking = false;
let currentLanguage = 'en';
let detectedLanguage = null;

// ============== DOM Elements ==============
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const interruptBtn = document.getElementById('interruptBtn');
const statusIndicator = document.getElementById('statusIndicator');
const statusText = document.getElementById('statusText');
const transcript = document.getElementById('transcript');
const errorMessage = document.getElementById('errorMessage');
const audioVisualizer = document.getElementById('audioVisualizer');
const detectedLanguageEl = document.getElementById('detectedLanguage');
const langNameEl = document.getElementById('langName');
const audioMeter = document.getElementById('audioMeter');
const visualizerLabel = document.getElementById('visualizerLabel');
const languageBadges = document.querySelectorAll('.lang-badge');

// ======================================================================
// LINEAR INTERPOLATION RESAMPLER (Shared Utility)
// ======================================================================

class LinearResampler {
    /**
     * Resample audio using high-quality linear interpolation
     * @param {Float32Array} input - Input samples
     * @param {number} inputRate - Input sample rate
     * @param {number} outputRate - Output sample rate
     * @returns {Float32Array} - Resampled output
     */
    static resample(input, inputRate, outputRate) {
        if (inputRate === outputRate) {
            return input;
        }
        
        const ratio = inputRate / outputRate;
        const outputLength = Math.floor(input.length / ratio);
        const output = new Float32Array(outputLength);
        
        for (let i = 0; i < outputLength; i++) {
            const srcIndex = i * ratio;
            const srcIndexFloor = Math.floor(srcIndex);
            const srcIndexCeil = Math.min(srcIndexFloor + 1, input.length - 1);
            const fraction = srcIndex - srcIndexFloor;
            
            // Linear interpolation: y = y0 + (y1 - y0) * t
            output[i] = input[srcIndexFloor] + (input[srcIndexCeil] - input[srcIndexFloor]) * fraction;
        }
        
        return output;
    }
    
    /**
     * Convert Float32 [-1, 1] to Int16 [-32768, 32767]
     */
    static float32ToInt16(float32Array) {
        const int16Array = new Int16Array(float32Array.length);
        for (let i = 0; i < float32Array.length; i++) {
            const s = Math.max(-1, Math.min(1, float32Array[i]));
            int16Array[i] = s < 0 ? s * 32768 : s * 32767;
        }
        return int16Array;
    }
    
    /**
     * Convert Int16 [-32768, 32767] to Float32 [-1, 1]
     */
    static int16ToFloat32(int16Array) {
        const float32Array = new Float32Array(int16Array.length);
        for (let i = 0; i < int16Array.length; i++) {
            float32Array[i] = int16Array[i] / 32768.0;
        }
        return float32Array;
    }
}

// ======================================================================
// AUDIO RECORDER CLASS (Microphone → Gemini) WITH RATE LIMITING
// ======================================================================

class AudioRecorder {
    constructor(onAudioData) {
        this.onAudioData = onAudioData;
        this.audioContext = null;
        this.mediaStream = null;
        this.scriptProcessor = null;
        this.micSource = null;
        this.inputSampleRate = 44100;
        this.isRecording = false;
        
        // Rate limiting - accumulate samples and send at fixed intervals
        this.sampleBuffer = [];
        this.sendInterval = null;
        this.lastSendTime = 0;
    }
    
    async start() {
        try {
            // Request microphone with optimal settings
            this.mediaStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });
            
            // Create AudioContext - browser will use its native rate
            this.audioContext = new AudioContext();
            this.inputSampleRate = this.audioContext.sampleRate;
            
            console.log(`🎤 Microphone: ${this.inputSampleRate}Hz → Resampling to ${GEMINI_INPUT_RATE}Hz`);
            console.log(`🎤 Rate limiting: Sending chunks every ${INPUT_CHUNK_INTERVAL_MS}ms`);
            
            // Create source from microphone
            this.micSource = this.audioContext.createMediaStreamSource(this.mediaStream);
            
            // ScriptProcessor for capturing audio (2048 samples for lower latency)
            this.scriptProcessor = this.audioContext.createScriptProcessor(2048, 1, 1);
            
            // Accumulate samples instead of sending immediately
            this.scriptProcessor.onaudioprocess = (event) => {
                if (!this.isRecording) return;
                
                const inputData = event.inputBuffer.getChannelData(0);
                
                // Calculate RMS for visualization
                let sum = 0;
                for (let i = 0; i < inputData.length; i++) {
                    sum += inputData[i] * inputData[i];
                }
                const rms = Math.sqrt(sum / inputData.length);
                
                // Store samples in buffer (copy to avoid reference issues)
                this.sampleBuffer.push({
                    samples: new Float32Array(inputData),
                    rms: rms
                });
            };
            
            // Connect: Mic → Processor → Muted output
            this.micSource.connect(this.scriptProcessor);
            
            const muteGain = this.audioContext.createGain();
            muteGain.gain.value = 0;
            this.scriptProcessor.connect(muteGain);
            muteGain.connect(this.audioContext.destination);
            
            this.isRecording = true;
            this.sampleBuffer = [];
            this.lastSendTime = performance.now();
            
            // Start rate-limited sending interval
            this.sendInterval = setInterval(() => this._sendBufferedAudio(), INPUT_CHUNK_INTERVAL_MS);
            
            console.log('🎤 Audio recording started with rate limiting');
            
            return this.inputSampleRate;
            
        } catch (error) {
            console.error('❌ Error starting audio recording:', error);
            throw error;
        }
    }
    
    /**
     * Send accumulated audio at fixed intervals (rate limiting)
     * @private
     */
    _sendBufferedAudio() {
        if (!this.isRecording || this.sampleBuffer.length === 0) return;
        
        // Concatenate all buffered samples
        const totalLength = this.sampleBuffer.reduce((sum, b) => sum + b.samples.length, 0);
        const combined = new Float32Array(totalLength);
        let offset = 0;
        let maxRms = 0;
        
        for (const buffer of this.sampleBuffer) {
            combined.set(buffer.samples, offset);
            offset += buffer.samples.length;
            maxRms = Math.max(maxRms, buffer.rms);
        }
        
        // Clear buffer
        this.sampleBuffer = [];
        
        // Resample to 16kHz using linear interpolation
        const resampled = LinearResampler.resample(
            combined, 
            this.inputSampleRate, 
            GEMINI_INPUT_RATE
        );
        
        // Convert to Int16
        const int16Data = LinearResampler.float32ToInt16(resampled);
        
        // Send to callback
        this.onAudioData(int16Data, maxRms);
    }
    
    stop() {
        this.isRecording = false;
        
        // Clear send interval
        if (this.sendInterval) {
            clearInterval(this.sendInterval);
            this.sendInterval = null;
        }
        
        this.sampleBuffer = [];
        
        if (this.scriptProcessor) {
            this.scriptProcessor.disconnect();
            this.scriptProcessor = null;
        }
        
        if (this.micSource) {
            this.micSource.disconnect();
            this.micSource = null;
        }
        
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }
        
        if (this.audioContext && this.audioContext.state !== 'closed') {
            this.audioContext.close();
            this.audioContext = null;
        }
        
        console.log('🎤 Audio recording stopped');
    }
}

// ======================================================================
// AUDIO STREAMER CLASS (Gemini → Speaker) WITH QUEUE-BASED RATE LIMITING
// ======================================================================

class AudioStreamer {
    constructor() {
        this.audioContext = null;
        this.gainNode = null;
        this.outputSampleRate = 44100;
        
        // Queue-based rate limiting - chunks go into queue, processed at fixed rate
        this.chunkQueue = [];              // Queue of resampled chunks waiting to be scheduled
        this.processInterval = null;       // Interval for processing queue
        this.isProcessing = false;         // Prevent re-entry
        
        // Initial Buffering State
        this.isBuffering = true;           // Start in buffering mode
        this.bufferingStartTime = 0;       // Track when buffering started
        
        // Playback scheduling
        this.nextStartTime = 0;
        this.scheduledSources = [];        // Track scheduled sources for interruption
        this.isPlaying = false;
        
        // Statistics
        this.chunksReceived = 0;
        this.chunksScheduled = 0;
        this.underruns = 0;
    }
    
    async initialize() {
        // Create AudioContext - browser chooses optimal rate
        this.audioContext = new AudioContext();
        this.outputSampleRate = this.audioContext.sampleRate;
        
        console.log(`🔊 Playback: ${GEMINI_OUTPUT_RATE}Hz → Resampling to ${this.outputSampleRate}Hz`);
        console.log(`🔊 Initial Buffer: Wait for ${INITIAL_BUFFER_CHUNKS} chunks before playing`);
        console.log(`🔊 Jitter Buffer: ${JITTER_BUFFER_MS}ms look-ahead`);
        console.log(`🔊 Output Rate Limiting: Process queue every ${OUTPUT_PROCESS_INTERVAL_MS}ms`);
        
        // Create gain node for volume control and smooth interruption
        this.gainNode = this.audioContext.createGain();
        this.gainNode.gain.value = 1.0;
        this.gainNode.connect(this.audioContext.destination);
        
        // Resume context (required after user interaction)
        if (this.audioContext.state === 'suspended') {
            await this.audioContext.resume();
        }
        
        // Reset all state
        this._resetState();
        
        // Start the queue processor
        this._startQueueProcessor();
        
        console.log('🔊 Audio streamer initialized');
        return this.outputSampleRate;
    }
    
    _resetState() {
        this.chunkQueue = [];
        this.nextStartTime = 0;
        this.scheduledSources = [];
        this.isPlaying = false;
        this.isBuffering = true;
        this.bufferingStartTime = 0;
        this.chunksReceived = 0;
        this.chunksScheduled = 0;
        this.underruns = 0;
    }
    
    _startQueueProcessor() {
        // Process queue at fixed intervals to prevent burst scheduling
        if (this.processInterval) {
            clearInterval(this.processInterval);
        }
        this.processInterval = setInterval(() => this._processQueue(), OUTPUT_PROCESS_INTERVAL_MS);
    }
    
    _stopQueueProcessor() {
        if (this.processInterval) {
            clearInterval(this.processInterval);
            this.processInterval = null;
        }
    }
    
    /**
     * Process chunks from the queue at a controlled rate
     * @private
     */
    _processQueue() {
        if (this.isProcessing || !this.audioContext || this.audioContext.state === 'closed') {
            return;
        }
        
        this.isProcessing = true;
        
        try {
            // Still in initial buffering mode?
            if (this.isBuffering) {
                const bufferTime = this.bufferingStartTime > 0 ? performance.now() - this.bufferingStartTime : 0;
                const hasEnoughChunks = this.chunkQueue.length >= INITIAL_BUFFER_CHUNKS;
                const hasWaitedLongEnough = this.bufferingStartTime > 0 && bufferTime >= 150;
                
                if (hasEnoughChunks || hasWaitedLongEnough) {
                    console.log(`🔊 Initial buffer ready: ${this.chunkQueue.length} chunks in ${bufferTime.toFixed(0)}ms`);
                    this.isBuffering = false;
                    
                    // Set initial start time with jitter buffer
                    const currentTime = this.audioContext.currentTime;
                    this.nextStartTime = currentTime + (JITTER_BUFFER_MS / 1000);
                    
                    // Schedule all buffered chunks at once
                    console.log(`🔊 Scheduling ${this.chunkQueue.length} buffered chunks starting at +${JITTER_BUFFER_MS}ms`);
                    while (this.chunkQueue.length > 0) {
                        const chunk = this.chunkQueue.shift();
                        this._scheduleChunkInternal(chunk);
                    }
                    this.isPlaying = true;
                }
                // If still buffering, don't process anything yet
                this.isProcessing = false;
                return;
            }
            
            // Normal mode - process ONE chunk per interval to prevent burst
            if (this.chunkQueue.length > 0) {
                const currentTime = this.audioContext.currentTime;
                
                // Only schedule if we need more audio scheduled ahead
                // This prevents scheduling too many chunks at once
                const bufferAhead = this.nextStartTime - currentTime;
                
                // Keep ~200ms of audio scheduled ahead
                if (bufferAhead < 0.2) {
                    // Check for underrun
                    if (this.nextStartTime <= currentTime && this.isPlaying) {
                        this.underruns++;
                        console.warn(`⚠️ Buffer underrun #${this.underruns}, rebuilding buffer`);
                        this.nextStartTime = currentTime + (JITTER_BUFFER_MS / 1000);
                    }
                    
                    const chunk = this.chunkQueue.shift();
                    this._scheduleChunkInternal(chunk);
                    this.isPlaying = true;
                }
            }
        } finally {
            this.isProcessing = false;
        }
    }
    
    /**
     * Reset to buffering mode (for new AI response)
     */
    resetBuffering() {
        this.chunkQueue = [];
        this.isBuffering = true;
        this.bufferingStartTime = 0;
        this.nextStartTime = 0;
        this.isPlaying = false;
        console.log('🔊 Reset to buffering mode');
    }
    
    /**
     * Add audio chunk to the queue
     * @param {string} base64Data - Base64 encoded 24kHz Int16 PCM
     * @returns {Float32Array} - Original samples for visualization
     */
    addChunk(base64Data) {
        if (!this.audioContext || this.audioContext.state === 'closed') {
            return null;
        }
        
        this.chunksReceived++;
        
        // Decode base64 → bytes → Int16
        const binaryString = atob(base64Data);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        const int16Data = new Int16Array(bytes.buffer);
        
        // Convert Int16 → Float32
        const float32Data = LinearResampler.int16ToFloat32(int16Data);
        
        // Resample 24kHz → browser rate using linear interpolation
        const resampled = LinearResampler.resample(
            float32Data,
            GEMINI_OUTPUT_RATE,
            this.outputSampleRate
        );
        
        // Add to queue - will be processed by the interval
        this.chunkQueue.push(resampled);
        
        // Start buffering timer on first chunk
        if (this.isBuffering && this.bufferingStartTime === 0) {
            this.bufferingStartTime = performance.now();
            console.log('🔊 Started initial buffering...');
        }
        
        return float32Data;  // Return original for visualization
    }
    
    /**
     * Internal chunk scheduling
     * @param {Float32Array} samples - Resampled audio samples
     * @private
     */
    _scheduleChunkInternal(samples) {
        // Resume context if suspended
        if (this.audioContext.state === 'suspended') {
            this.audioContext.resume();
        }
        
        // Create audio buffer at browser's sample rate
        const audioBuffer = this.audioContext.createBuffer(
            1, 
            samples.length, 
            this.outputSampleRate
        );
        audioBuffer.getChannelData(0).set(samples);
        
        // Calculate chunk duration
        const duration = samples.length / this.outputSampleRate;
        const currentTime = this.audioContext.currentTime;
        
        // Ensure nextStartTime is valid
        if (this.nextStartTime < currentTime) {
            this.nextStartTime = currentTime + 0.01;
        }
        
        // Create buffer source
        const source = this.audioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(this.gainNode);
        
        // Schedule playback at exact time
        source.start(this.nextStartTime);
        
        // Track source for potential interruption
        this.scheduledSources.push({
            source: source,
            startTime: this.nextStartTime,
            endTime: this.nextStartTime + duration
        });
        
        // Clean up finished sources
        this.scheduledSources = this.scheduledSources.filter(s => s.endTime > currentTime);
        
        // Update nextStartTime for next chunk
        this.nextStartTime += duration;
        
        // Prevent buffer from growing too large (max 2 seconds ahead)
        if (this.nextStartTime > currentTime + 2) {
            console.warn('⚠️ Buffer overflow, resetting to prevent latency');
            this.nextStartTime = currentTime + (SAFETY_MARGIN_MS / 1000);
        }
        
        this.chunksScheduled++;
    }
    
    /**
     * Interrupt playback immediately (for barge-in)
     */
    async interrupt() {
        if (!this.audioContext) return;
        
        console.log(`🛑 Interrupting: ${this.scheduledSources.length} scheduled, ${this.chunkQueue.length} queued`);
        
        // 1. Clear the queue first!
        this.chunkQueue = [];
        this.isBuffering = true;
        this.bufferingStartTime = 0;
        
        // 2. Immediately fade out to prevent click
        const currentTime = this.audioContext.currentTime;
        this.gainNode.gain.setTargetAtTime(0, currentTime, 0.015);
        
        // 3. Stop all scheduled sources
        for (const scheduled of this.scheduledSources) {
            try {
                scheduled.source.stop();
            } catch (e) {
                // Source may have already finished
            }
        }
        this.scheduledSources = [];
        
        // 4. Suspend audio context to stop all processing
        if (this.audioContext.state === 'running') {
            await this.audioContext.suspend();
        }
        
        // 5. Resume after brief pause
        setTimeout(async () => {
            if (this.audioContext && this.audioContext.state === 'suspended') {
                await this.audioContext.resume();
            }
            // Reset gain
            if (this.gainNode) {
                this.gainNode.gain.value = 1.0;
            }
        }, 30);
        
        // 6. Reset scheduling state
        this.nextStartTime = 0;
        this.isPlaying = false;
        
        console.log('🛑 Playback interrupted and cleared');
    }
    
    /**
     * Get current playback statistics
     */
    getStats() {
        return {
            chunksReceived: this.chunksReceived,
            chunksScheduled: this.chunksScheduled,
            queueLength: this.chunkQueue.length,
            underruns: this.underruns,
            scheduledSources: this.scheduledSources.length,
            isBuffering: this.isBuffering,
            bufferAhead: this.nextStartTime - (this.audioContext?.currentTime || 0)
        };
    }
    
    /**
     * Stop and clean up streamer
     */
    stop() {
        this._stopQueueProcessor();
        this.interrupt();
        
        if (this.audioContext && this.audioContext.state !== 'closed') {
            this.audioContext.close();
        }
        
        this.audioContext = null;
        this.gainNode = null;
        this._resetState();
        
        console.log(`🔊 Streamer stopped. Stats: ${this.chunksScheduled}/${this.chunksReceived} chunks, ${this.underruns} underruns`);
    }
}

// ======================================================================
// VISUALIZER FUNCTIONS
// ======================================================================

function initVisualizer() {
    audioVisualizer.innerHTML = '';
    for (let i = 0; i < NUM_VISUALIZER_BARS; i++) {
        const bar = document.createElement('div');
        bar.className = 'visualizer-bar';
        bar.style.height = '4px';
        audioVisualizer.appendChild(bar);
    }
}

function updateVisualizer(values) {
    const bars = audioVisualizer.children;
    const step = Math.max(1, Math.floor(values.length / bars.length));
    
    for (let i = 0; i < bars.length; i++) {
        const value = values[i * step] || 0;
        const height = Math.max(4, value * 70);
        bars[i].style.height = `${height}px`;
    }
}

function resetVisualizer() {
    const bars = audioVisualizer.children;
    for (let i = 0; i < bars.length; i++) {
        bars[i].style.height = '4px';
    }
}

function updateAudioMeter(level) {
    const meterBars = audioMeter.querySelectorAll('.meter-bar');
    const normalizedLevel = Math.min(1, level * 2);
    
    meterBars.forEach((bar, i) => {
        const threshold = (i + 1) / meterBars.length;
        if (normalizedLevel >= threshold) {
            bar.classList.add('active');
            bar.style.height = `${4 + (normalizedLevel - threshold) * 16}px`;
        } else {
            bar.classList.remove('active');
            bar.style.height = '4px';
        }
    });
}

function animateVisualizerForAudio(samples) {
    let rms = 0.3;
    
    if (samples && samples.length > 0) {
        let sum = 0;
        for (let i = 0; i < samples.length; i++) {
            sum += samples[i] * samples[i];
        }
        rms = Math.sqrt(sum / samples.length);
    }
    
    const vizData = Array(NUM_VISUALIZER_BARS).fill(0).map((_, i) => {
        const phase = Date.now() / 80 + i * 0.35;
        const wave = Math.sin(phase) * 0.3 + Math.cos(phase * 0.7) * 0.2;
        return Math.max(0.08, (rms * 5) + wave * 0.5);
    });
    updateVisualizer(vizData);
}

// ======================================================================
// STATUS & UI FUNCTIONS
// ======================================================================

function setStatus(status, text) {
    statusIndicator.className = 'status-indicator ' + status;
    statusText.textContent = text;
}

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
    setTimeout(() => {
        errorMessage.style.display = 'none';
    }, 5000);
}

function updateDetectedLanguage(lang) {
    detectedLanguage = lang;
    
    const langNames = {
        'en': 'English',
        'hi': 'Hindi (हिंदी)',
        'gu': 'Gujarati (ગુજરાતી)',
        'english': 'English',
        'hindi': 'Hindi (हिंदी)',
        'gujarati': 'Gujarati (ગુજરાતી)'
    };
    
    const langCode = lang.toLowerCase().substring(0, 2);
    langNameEl.textContent = langNames[lang] || langNames[langCode] || lang;
    detectedLanguageEl.style.display = 'flex';
    detectedLanguageEl.classList.add('active');
    
    languageBadges.forEach(badge => {
        badge.classList.remove('active');
        if (badge.dataset.lang === langCode) {
            badge.classList.add('active');
        }
    });
}

function appendTranscript(text, speaker = 'ai', lang = null) {
    const entry = document.createElement('div');
    entry.className = `transcript-entry ${speaker}`;
    
    const speakerLabel = speaker === 'ai' ? '🤖 AI Interviewer' : '👤 Candidate';
    const langIndicator = lang ? ` (${lang})` : '';
    
    entry.innerHTML = `
        <div class="speaker">${speakerLabel}${langIndicator}</div>
        <div>${text}</div>
    `;
    
    transcript.appendChild(entry);
    transcript.scrollTop = transcript.scrollHeight;
}

function clearTranscript() {
    transcript.innerHTML = '';
}

// ======================================================================
// WEBSOCKET COMMUNICATION
// ======================================================================

function connectWebSocket() {
    return new Promise((resolve, reject) => {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        console.log('🔌 Connecting to WebSocket:', wsUrl);
        websocket = new WebSocket(wsUrl);
        
        websocket.onopen = () => {
            console.log('✅ WebSocket connected');
            setStatus('connected', 'Connected - Setting up Gemini...');
            resolve();
        };
        
        websocket.onclose = (event) => {
            console.log('🔌 WebSocket closed:', event.code, event.reason);
            if (isInterviewActive) {
                setStatus('', 'Disconnected');
                stopInterview();
            }
        };
        
        websocket.onerror = (error) => {
            console.error('❌ WebSocket error:', error);
            showError('Connection error. Please try again.');
            reject(error);
        };
        
        websocket.onmessage = (event) => {
            handleServerMessage(JSON.parse(event.data));
        };
    });
}

function handleServerMessage(data) {
    switch (data.type) {
        case 'setup_complete':
            console.log('✅ Gemini setup complete');
            setStatus('user-speaking', 'Listening... Speak in any language!');
            interruptBtn.disabled = false;
            break;
            
        case 'audio':
            // Gemini sends 24kHz Int16 PCM as base64
            handleGeminiAudio(data.data);
            break;
            
        case 'transcript':
            if (data.text) {
                appendTranscript(data.text, 'ai', data.language);
                if (data.language) {
                    updateDetectedLanguage(data.language);
                }
            }
            break;
            
        case 'text':
            appendTranscript(data.data, 'ai');
            break;
            
        case 'interrupted':
            console.log('🛑 AI interrupted - clearing playback');
            if (audioStreamer) {
                audioStreamer.interrupt();
            }
            isAISpeaking = false;
            setStatus('user-speaking', 'Listening...');
            visualizerLabel.textContent = 'Your Audio';
            resetVisualizer();
            break;
            
        case 'turn_complete':
            console.log('✅ AI turn complete');
            isAISpeaking = false;
            setStatus('user-speaking', 'Your turn - Speak now');
            visualizerLabel.textContent = 'Your Audio';
            
            // Log playback stats and reset buffering for next response
            if (audioStreamer) {
                const stats = audioStreamer.getStats();
                console.log(`📊 Playback stats: ${stats.chunksScheduled}/${stats.chunksReceived} chunks scheduled, ${stats.underruns} underruns, queue: ${stats.queueLength}`);
                // Reset buffering mode for next AI response
                audioStreamer.resetBuffering();
            }
            break;
            
        case 'error':
            console.error('❌ Server error:', data.message);
            showError(data.message || 'Server error occurred');
            break;
    }
}

// ======================================================================
// AUDIO HANDLERS
// ======================================================================

/**
 * Handle incoming audio from Gemini (24kHz Int16 PCM as base64)
 */
function handleGeminiAudio(base64Data) {
    if (!audioStreamer) return;
    
    // Add to jitter buffer and get original samples for visualization
    const originalSamples = audioStreamer.addChunk(base64Data);
    
    if (originalSamples) {
        // Update UI
        isAISpeaking = true;
        setStatus('ai-speaking', 'AI is speaking...');
        visualizerLabel.textContent = 'AI Audio';
        
        // Animate visualizer
        animateVisualizerForAudio(originalSamples);
    }
}

/**
 * Handle outgoing audio to Gemini (from microphone)
 */
function handleMicrophoneAudio(int16Data, rms) {
    if (!isInterviewActive || !websocket || websocket.readyState !== WebSocket.OPEN) {
        return;
    }
    
    // Update visualizer if not AI speaking
    if (!isAISpeaking && rms > 0.01) {
        updateAudioMeter(rms);
        const vizData = Array(NUM_VISUALIZER_BARS).fill(0).map((_, i) => {
            return rms * (1 + Math.sin(Date.now() / 100 + i * 0.3) * 0.3);
        });
        updateVisualizer(vizData);
    }
    
    // Convert to base64 and send
    const base64Data = arrayBufferToBase64(int16Data.buffer);
    websocket.send(JSON.stringify({
        type: 'audio',
        data: base64Data
    }));
}

// ======================================================================
// UTILITY FUNCTIONS
// ======================================================================

function arrayBufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    const chunkSize = 32768;
    
    for (let i = 0; i < bytes.length; i += chunkSize) {
        const chunk = bytes.subarray(i, i + chunkSize);
        binary += String.fromCharCode.apply(null, chunk);
    }
    
    return btoa(binary);
}

// ======================================================================
// INTERVIEW CONTROL
// ======================================================================

async function startInterview() {
    try {
        startBtn.disabled = true;
        interruptBtn.disabled = true;
        setStatus('', 'Connecting...');
        
        // Initialize visualizer
        initVisualizer();
        
        // Initialize AudioStreamer (playback with jitter buffer)
        audioStreamer = new AudioStreamer();
        const outputRate = await audioStreamer.initialize();
        
        // Connect WebSocket
        await connectWebSocket();
        
        // Initialize AudioRecorder (microphone with resampling)
        audioRecorder = new AudioRecorder(handleMicrophoneAudio);
        const inputRate = await audioRecorder.start();
        
        isInterviewActive = true;
        stopBtn.disabled = false;
        
        // Clear previous transcript
        clearTranscript();
        
        // Reset language detection
        detectedLanguageEl.style.display = 'none';
        
        console.log('🎙️ Interview started - Professional Grade Audio');
        console.log(`📊 Input Pipeline: Mic(${inputRate}Hz) → Resample → ${GEMINI_INPUT_RATE}Hz → Gemini`);
        console.log(`📊 Output Pipeline: Gemini → ${GEMINI_OUTPUT_RATE}Hz → Resample → ${outputRate}Hz → Jitter Buffer(${JITTER_BUFFER_MS}ms) → Speaker`);
        
    } catch (error) {
        console.error('❌ Error starting interview:', error);
        showError('Failed to start interview. Please check microphone permissions.');
        setStatus('', 'Error - Click Start to retry');
        startBtn.disabled = false;
        interruptBtn.disabled = true;
    }
}

async function interruptAI() {
    if (!isInterviewActive) return;
    
    console.log('✋ User requested interrupt');
    
    // 1. Clear local playback immediately with proper suspension
    if (audioStreamer) {
        await audioStreamer.interrupt();
    }
    
    // 2. Send interrupt signal to server
    if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.send(JSON.stringify({ type: 'interrupt' }));
    }
    
    isAISpeaking = false;
    setStatus('user-speaking', 'Listening...');
    visualizerLabel.textContent = 'Your Audio';
    resetVisualizer();
}

function stopInterview() {
    isInterviewActive = false;
    
    // Send stop signal
    if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.send(JSON.stringify({ type: 'stop' }));
        websocket.close();
    }
    websocket = null;
    
    // Stop recorder
    if (audioRecorder) {
        audioRecorder.stop();
        audioRecorder = null;
    }
    
    // Stop streamer
    if (audioStreamer) {
        audioStreamer.stop();
        audioStreamer = null;
    }
    
    // Update UI
    startBtn.disabled = false;
    stopBtn.disabled = true;
    interruptBtn.disabled = true;
    setStatus('', 'Interview ended');
    resetVisualizer();
    detectedLanguageEl.style.display = 'none';
    isAISpeaking = false;
    
    console.log('🏁 Interview stopped');
}

// ======================================================================
// INITIALIZATION
// ======================================================================

document.addEventListener('DOMContentLoaded', () => {
    initVisualizer();
    
    // Language badge click handlers (informational only)
    languageBadges.forEach(badge => {
        badge.addEventListener('click', () => {
            languageBadges.forEach(b => b.classList.remove('active'));
            badge.classList.add('active');
        });
    });
    
    console.log('🚀 Multilingual AI Interviewer - Professional Grade Audio');
    console.log('📝 Supported languages: English, Hindi (हिंदी), Gujarati (ગુજરાతી)');
    console.log('Features: Rate-limited Input (100ms), Initial Buffering (3 chunks), Jitter Buffer (100ms), Barge-in');
});

// Handle page unload
window.addEventListener('beforeunload', () => {
    if (isInterviewActive) {
        stopInterview();
    }
});
