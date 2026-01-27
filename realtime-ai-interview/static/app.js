/**
 * Live AI Interview - Professional Grade Audio & Video
 * =====================================================
 * 
 * Features:
 * - Live camera feed with mirror effect
 * - 16kHz 16-bit PCM mono audio capture
 * - Real-time transcription display
 * - Interim (ghost) text support
 * - WebSocket communication with Gemini API proxy
 * - Professional status indicators
 * 
 * Audio Pipeline:
 * ===============
 * INPUT:  Browser Mic (44.1/48kHz) → Linear Resampler → 16kHz Int16 → Base64 → WebSocket
 * OUTPUT: WebSocket → Base64 → 24kHz Int16 → Linear Resampler → Browser Rate → Speaker
 */

// ============== Configuration ==============
const GEMINI_INPUT_RATE = 16000;      // What Gemini expects
const GEMINI_OUTPUT_RATE = 24000;     // What Gemini sends
const JITTER_BUFFER_MS = 100;         // Look-ahead buffer for smooth playback
const INITIAL_BUFFER_CHUNKS = 3;      // Wait for N chunks before playing
const INPUT_CHUNK_INTERVAL_MS = 100;  // Send input every 100ms
const OUTPUT_PROCESS_INTERVAL_MS = 20; // Process output every 20ms

// ============== State ==============
let websocket = null;
let audioStreamer = null;
let audioRecorder = null;
let videoStream = null;
let isInterviewActive = false;
let isAISpeaking = false;
let sessionStartTime = null;
let timerInterval = null;
let selectedCameraId = null;
let availableCameras = [];

// ============== DOM Elements ==============
const videoFeed = document.getElementById('videoFeed');
const videoPlaceholder = document.getElementById('videoPlaceholder');
const videoOverlay = document.getElementById('videoOverlay');
const recordingIndicator = document.getElementById('recordingIndicator');
const audioLevel = document.getElementById('audioLevel');
const liveBadge = document.getElementById('liveBadge');
const sessionTimer = document.getElementById('sessionTimer');
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const interruptBtn = document.getElementById('interruptBtn');
const micStatus = document.getElementById('micStatus');
const connectionStatus = document.getElementById('connectionStatus');
const aiStatus = document.getElementById('aiStatus');
const aiSpeakingBar = document.getElementById('aiSpeakingBar');
const errorBanner = document.getElementById('errorBanner');
const errorText = document.getElementById('errorText');
const transcript = document.getElementById('transcript');
const transcriptPlaceholder = document.getElementById('transcriptPlaceholder');
const transcriptContainer = document.getElementById('transcriptContainer');
const interimTranscript = document.getElementById('interimTranscript');
const languageBadges = document.querySelectorAll('.lang-badge');
const cameraSelect = document.getElementById('cameraSelect');
const refreshCamerasBtn = document.getElementById('refreshCameras');

// ======================================================================
// LINEAR INTERPOLATION RESAMPLER
// ======================================================================

class LinearResampler {
    static resample(input, inputRate, outputRate) {
        if (inputRate === outputRate) return input;
        
        const ratio = inputRate / outputRate;
        const outputLength = Math.floor(input.length / ratio);
        const output = new Float32Array(outputLength);
        
        for (let i = 0; i < outputLength; i++) {
            const srcIndex = i * ratio;
            const srcIndexFloor = Math.floor(srcIndex);
            const srcIndexCeil = Math.min(srcIndexFloor + 1, input.length - 1);
            const fraction = srcIndex - srcIndexFloor;
            output[i] = input[srcIndexFloor] + (input[srcIndexCeil] - input[srcIndexFloor]) * fraction;
        }
        
        return output;
    }
    
    static float32ToInt16(float32Array) {
        const int16Array = new Int16Array(float32Array.length);
        for (let i = 0; i < float32Array.length; i++) {
            const s = Math.max(-1, Math.min(1, float32Array[i]));
            int16Array[i] = s < 0 ? s * 32768 : s * 32767;
        }
        return int16Array;
    }
    
    static int16ToFloat32(int16Array) {
        const float32Array = new Float32Array(int16Array.length);
        for (let i = 0; i < int16Array.length; i++) {
            float32Array[i] = int16Array[i] / 32768.0;
        }
        return float32Array;
    }
}

// ======================================================================
// AUDIO RECORDER CLASS (Microphone → Gemini)
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
        this.sampleBuffer = [];
        this.sendInterval = null;
    }
    
    async start() {
        try {
            this.mediaStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });
            
            this.audioContext = new AudioContext();
            this.inputSampleRate = this.audioContext.sampleRate;
            
            console.log(`🎤 Microphone: ${this.inputSampleRate}Hz → Resampling to ${GEMINI_INPUT_RATE}Hz`);
            
            this.micSource = this.audioContext.createMediaStreamSource(this.mediaStream);
            this.scriptProcessor = this.audioContext.createScriptProcessor(2048, 1, 1);
            
            this.scriptProcessor.onaudioprocess = (event) => {
                if (!this.isRecording) return;
                
                const inputData = event.inputBuffer.getChannelData(0);
                let sum = 0;
                for (let i = 0; i < inputData.length; i++) {
                    sum += inputData[i] * inputData[i];
                }
                const rms = Math.sqrt(sum / inputData.length);
                
                this.sampleBuffer.push({
                    samples: new Float32Array(inputData),
                    rms: rms
                });
            };
            
            this.micSource.connect(this.scriptProcessor);
            const muteGain = this.audioContext.createGain();
            muteGain.gain.value = 0;
            this.scriptProcessor.connect(muteGain);
            muteGain.connect(this.audioContext.destination);
            
            this.isRecording = true;
            this.sampleBuffer = [];
            
            this.sendInterval = setInterval(() => this._sendBufferedAudio(), INPUT_CHUNK_INTERVAL_MS);
            
            return this.inputSampleRate;
        } catch (error) {
            console.error('❌ Error starting audio recording:', error);
            throw error;
        }
    }
    
    _sendBufferedAudio() {
        if (!this.isRecording || this.sampleBuffer.length === 0) return;
        
        const totalLength = this.sampleBuffer.reduce((sum, b) => sum + b.samples.length, 0);
        const combined = new Float32Array(totalLength);
        let offset = 0;
        let maxRms = 0;
        
        for (const buffer of this.sampleBuffer) {
            combined.set(buffer.samples, offset);
            offset += buffer.samples.length;
            maxRms = Math.max(maxRms, buffer.rms);
        }
        
        this.sampleBuffer = [];
        
        const resampled = LinearResampler.resample(combined, this.inputSampleRate, GEMINI_INPUT_RATE);
        const int16Data = LinearResampler.float32ToInt16(resampled);
        
        this.onAudioData(int16Data, maxRms);
    }
    
    stop() {
        this.isRecording = false;
        
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
// AUDIO STREAMER CLASS (Gemini → Speaker)
// ======================================================================

class AudioStreamer {
    constructor() {
        this.audioContext = null;
        this.gainNode = null;
        this.outputSampleRate = 44100;
        this.chunkQueue = [];
        this.processInterval = null;
        this.isProcessing = false;
        this.isBuffering = true;
        this.bufferingStartTime = 0;
        this.nextStartTime = 0;
        this.scheduledSources = [];
        this.isPlaying = false;
        this.chunksReceived = 0;
        this.chunksScheduled = 0;
    }
    
    async initialize() {
        this.audioContext = new AudioContext();
        this.outputSampleRate = this.audioContext.sampleRate;
        
        console.log(`🔊 Playback: ${GEMINI_OUTPUT_RATE}Hz → Resampling to ${this.outputSampleRate}Hz`);
        
        this.gainNode = this.audioContext.createGain();
        this.gainNode.gain.value = 1.0;
        this.gainNode.connect(this.audioContext.destination);
        
        if (this.audioContext.state === 'suspended') {
            await this.audioContext.resume();
        }
        
        this._resetState();
        this._startQueueProcessor();
        
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
    }
    
    _startQueueProcessor() {
        if (this.processInterval) clearInterval(this.processInterval);
        this.processInterval = setInterval(() => this._processQueue(), OUTPUT_PROCESS_INTERVAL_MS);
    }
    
    _stopQueueProcessor() {
        if (this.processInterval) {
            clearInterval(this.processInterval);
            this.processInterval = null;
        }
    }
    
    _processQueue() {
        if (this.isProcessing || !this.audioContext || this.audioContext.state === 'closed') return;
        
        this.isProcessing = true;
        
        try {
            if (this.isBuffering) {
                const bufferTime = this.bufferingStartTime > 0 ? performance.now() - this.bufferingStartTime : 0;
                const hasEnoughChunks = this.chunkQueue.length >= INITIAL_BUFFER_CHUNKS;
                const hasWaitedLongEnough = this.bufferingStartTime > 0 && bufferTime >= 150;
                
                if (hasEnoughChunks || hasWaitedLongEnough) {
                    this.isBuffering = false;
                    const currentTime = this.audioContext.currentTime;
                    this.nextStartTime = currentTime + (JITTER_BUFFER_MS / 1000);
                    
                    while (this.chunkQueue.length > 0) {
                        const chunk = this.chunkQueue.shift();
                        this._scheduleChunkInternal(chunk);
                    }
                    this.isPlaying = true;
                }
                this.isProcessing = false;
                return;
            }
            
            if (this.chunkQueue.length > 0) {
                const currentTime = this.audioContext.currentTime;
                const bufferAhead = this.nextStartTime - currentTime;
                
                if (bufferAhead < 0.2) {
                    if (this.nextStartTime <= currentTime && this.isPlaying) {
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
    
    resetBuffering() {
        this.chunkQueue = [];
        this.isBuffering = true;
        this.bufferingStartTime = 0;
        this.nextStartTime = 0;
        this.isPlaying = false;
    }
    
    addChunk(base64Data) {
        if (!this.audioContext || this.audioContext.state === 'closed') return null;
        
        this.chunksReceived++;
        
        const binaryString = atob(base64Data);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        const int16Data = new Int16Array(bytes.buffer);
        const float32Data = LinearResampler.int16ToFloat32(int16Data);
        const resampled = LinearResampler.resample(float32Data, GEMINI_OUTPUT_RATE, this.outputSampleRate);
        
        this.chunkQueue.push(resampled);
        
        if (this.isBuffering && this.bufferingStartTime === 0) {
            this.bufferingStartTime = performance.now();
        }
        
        return float32Data;
    }
    
    _scheduleChunkInternal(samples) {
        if (this.audioContext.state === 'suspended') {
            this.audioContext.resume();
        }
        
        const audioBuffer = this.audioContext.createBuffer(1, samples.length, this.outputSampleRate);
        audioBuffer.getChannelData(0).set(samples);
        
        const duration = samples.length / this.outputSampleRate;
        const currentTime = this.audioContext.currentTime;
        
        if (this.nextStartTime < currentTime) {
            this.nextStartTime = currentTime + 0.01;
        }
        
        const source = this.audioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(this.gainNode);
        source.start(this.nextStartTime);
        
        this.scheduledSources.push({
            source: source,
            startTime: this.nextStartTime,
            endTime: this.nextStartTime + duration
        });
        
        this.scheduledSources = this.scheduledSources.filter(s => s.endTime > currentTime);
        this.nextStartTime += duration;
        
        if (this.nextStartTime > currentTime + 2) {
            this.nextStartTime = currentTime + 0.05;
        }
        
        this.chunksScheduled++;
    }
    
    async interrupt() {
        if (!this.audioContext) return;
        
        this.chunkQueue = [];
        this.isBuffering = true;
        this.bufferingStartTime = 0;
        
        const currentTime = this.audioContext.currentTime;
        this.gainNode.gain.setTargetAtTime(0, currentTime, 0.015);
        
        for (const scheduled of this.scheduledSources) {
            try { scheduled.source.stop(); } catch (e) {}
        }
        this.scheduledSources = [];
        
        if (this.audioContext.state === 'running') {
            await this.audioContext.suspend();
        }
        
        setTimeout(async () => {
            if (this.audioContext && this.audioContext.state === 'suspended') {
                await this.audioContext.resume();
            }
            if (this.gainNode) {
                this.gainNode.gain.value = 1.0;
            }
        }, 30);
        
        this.nextStartTime = 0;
        this.isPlaying = false;
    }
    
    stop() {
        this._stopQueueProcessor();
        this.interrupt();
        
        if (this.audioContext && this.audioContext.state !== 'closed') {
            this.audioContext.close();
        }
        
        this.audioContext = null;
        this.gainNode = null;
        this._resetState();
    }
}

// ======================================================================
// VIDEO/CAMERA FUNCTIONS
// ======================================================================

// Enumerate all available video input devices (cameras)
async function enumerateCameras() {
    try {
        console.log('📷 Enumerating available cameras...');
        
        // First request temporary camera access to get full device labels
        // (Without this, device labels may be empty for privacy reasons)
        let tempStream = null;
        try {
            tempStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        } catch (e) {
            console.log('📷 Could not get temp stream for labels, using partial info');
        }
        
        const devices = await navigator.mediaDevices.enumerateDevices();
        const videoDevices = devices.filter(device => device.kind === 'videoinput');
        
        // Release temporary stream
        if (tempStream) {
            tempStream.getTracks().forEach(track => track.stop());
        }
        
        availableCameras = videoDevices;
        console.log(`📷 Found ${videoDevices.length} camera(s):`, videoDevices.map(d => d.label || d.deviceId));
        
        return videoDevices;
    } catch (error) {
        console.error('❌ Error enumerating cameras:', error);
        return [];
    }
}

// Populate the camera dropdown with available devices
async function populateCameraDropdown() {
    const cameras = await enumerateCameras();
    
    // Clear existing options except the first one
    cameraSelect.innerHTML = '<option value="">Select Camera...</option>';
    
    if (cameras.length === 0) {
        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'No cameras found';
        option.disabled = true;
        cameraSelect.appendChild(option);
        return;
    }
    
    cameras.forEach((camera, index) => {
        const option = document.createElement('option');
        option.value = camera.deviceId;
        
        // Use the label if available, otherwise create a generic name
        let label = camera.label || `Camera ${index + 1}`;
        
        // Identify common camera types for better UX
        if (label.toLowerCase().includes('virtual')) {
            label = `🖥️ ${label}`;
        } else if (label.toLowerCase().includes('droid') || label.toLowerCase().includes('phone')) {
            label = `📱 ${label}`;
        } else if (label.toLowerCase().includes('usb')) {
            label = `🔌 ${label}`;
        } else if (label.toLowerCase().includes('obs') || label.toLowerCase().includes('stream')) {
            label = `🎬 ${label}`;
        } else if (label.toLowerCase().includes('webcam') || label.toLowerCase().includes('integrated') || label.toLowerCase().includes('front')) {
            label = `📹 ${label}`;
        } else {
            label = `📷 ${label}`;
        }
        
        option.textContent = label;
        cameraSelect.appendChild(option);
    });
    
    // Auto-select the first camera if none selected
    if (!selectedCameraId && cameras.length > 0) {
        selectedCameraId = cameras[0].deviceId;
        cameraSelect.value = selectedCameraId;
    } else if (selectedCameraId) {
        cameraSelect.value = selectedCameraId;
    }
    
    console.log('📷 Camera dropdown populated');
}

// Refresh the camera list (called by refresh button)
async function refreshCameraList() {
    console.log('🔄 Refreshing camera list...');
    const btn = refreshCamerasBtn;
    btn.classList.add('loading');
    btn.disabled = true;
    
    await populateCameraDropdown();
    
    // Add slight delay for visual feedback
    setTimeout(() => {
        btn.classList.remove('loading');
        btn.disabled = false;
    }, 500);
}

// Handle camera selection change
function handleCameraChange(event) {
    const newCameraId = event.target.value;
    if (newCameraId && newCameraId !== selectedCameraId) {
        selectedCameraId = newCameraId;
        console.log('📷 Camera selected:', selectedCameraId);
        
        // If camera is already running, switch to new camera
        if (videoStream) {
            switchCamera(selectedCameraId);
        }
    }
}

// Switch to a different camera while streaming
async function switchCamera(deviceId) {
    try {
        console.log('📷 Switching camera to:', deviceId);
        
        // Stop current video tracks
        if (videoStream) {
            videoStream.getVideoTracks().forEach(track => track.stop());
        }
        
        // Start new camera
        const newStream = await navigator.mediaDevices.getUserMedia({
            video: {
                deviceId: { exact: deviceId },
                width: { ideal: 1280 },
                height: { ideal: 720 }
            },
            audio: false
        });
        
        videoStream = newStream;
        videoFeed.srcObject = newStream;
        
        console.log('📷 Camera switched successfully');
    } catch (error) {
        console.error('❌ Error switching camera:', error);
        showError('Failed to switch camera. Please try again.');
    }
}

async function startCamera() {
    try {
        console.log('📷 Starting camera...');
        
        const constraints = {
            video: {
                width: { ideal: 1280 },
                height: { ideal: 720 }
            },
            audio: false
        };
        
        // Use selected camera if available
        if (selectedCameraId) {
            constraints.video.deviceId = { exact: selectedCameraId };
            console.log('📷 Using selected camera:', selectedCameraId);
        } else {
            constraints.video.facingMode = 'user';
            console.log('📷 Using default front-facing camera');
        }
        
        videoStream = await navigator.mediaDevices.getUserMedia(constraints);
        
        videoFeed.srcObject = videoStream;
        videoFeed.classList.add('active');
        videoPlaceholder.classList.add('hidden');
        videoOverlay.classList.add('active');
        
        // Update selected camera ID with actual device being used
        const videoTrack = videoStream.getVideoTracks()[0];
        if (videoTrack) {
            const settings = videoTrack.getSettings();
            if (settings.deviceId && settings.deviceId !== selectedCameraId) {
                selectedCameraId = settings.deviceId;
                cameraSelect.value = selectedCameraId;
            }
        }
        
        console.log('📷 Camera started successfully');
        return true;
    } catch (error) {
        console.error('❌ Error starting camera:', error);
        
        // Provide specific error messages
        if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
            showError('Selected camera not found. Please choose another camera.');
        } else if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
            showError('Camera access denied. Please allow camera permissions.');
        } else if (error.name === 'NotReadableError' || error.name === 'TrackStartError') {
            showError('Camera is in use by another application. Please close other apps using the camera.');
        } else if (error.name === 'OverconstrainedError') {
            // Try again without specific device ID
            console.log('📷 Retrying with default camera...');
            selectedCameraId = null;
            return await startCamera();
        } else {
            showError('Failed to access camera. Please check your camera connection.');
        }
        return false;
    }
}

function stopCamera() {
    if (videoStream) {
        videoStream.getTracks().forEach(track => track.stop());
        videoStream = null;
    }
    videoFeed.srcObject = null;
    videoFeed.classList.remove('active');
    videoPlaceholder.classList.remove('hidden');
    videoOverlay.classList.remove('active');
    console.log('📷 Camera stopped');
}

// ======================================================================
// TIMER FUNCTIONS
// ======================================================================

function startTimer() {
    sessionStartTime = Date.now();
    liveBadge.classList.add('active');
    
    timerInterval = setInterval(() => {
        const elapsed = Date.now() - sessionStartTime;
        const hours = Math.floor(elapsed / 3600000);
        const minutes = Math.floor((elapsed % 3600000) / 60000);
        const seconds = Math.floor((elapsed % 60000) / 1000);
        sessionTimer.textContent = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }, 1000);
}

function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
    liveBadge.classList.remove('active');
    sessionStartTime = null;
}

// ======================================================================
// STATUS & UI FUNCTIONS
// ======================================================================

function updateMicStatus(active, text) {
    micStatus.classList.toggle('active', active);
    micStatus.querySelector('.status-text').textContent = text;
}

function updateConnectionStatus(active, text) {
    connectionStatus.classList.toggle('active', active);
    connectionStatus.querySelector('.status-text').textContent = text;
}

function updateAIStatus(active, speaking, text) {
    aiStatus.classList.toggle('active', active);
    aiStatus.classList.toggle('warning', speaking);
    aiStatus.querySelector('.status-text').textContent = text;
    
    aiSpeakingBar.classList.toggle('active', speaking);
}

function showError(message) {
    errorText.textContent = message;
    errorBanner.classList.add('active');
}

function hideError() {
    errorBanner.classList.remove('active');
}

function updateAudioLevel(level) {
    const bars = audioLevel.querySelectorAll('.level-bar');
    const normalizedLevel = Math.min(1, level * 3);
    
    bars.forEach((bar, i) => {
        const threshold = (i + 1) / bars.length;
        const height = normalizedLevel >= threshold ? 6 + (normalizedLevel - threshold) * 20 : 6;
        bar.style.height = `${height}px`;
    });
}

// ======================================================================
// TRANSCRIPT FUNCTIONS
// ======================================================================

function appendTranscript(text, speaker = 'ai', isInterim = false) {
    transcriptPlaceholder.classList.add('hidden');
    
    if (isInterim) {
        interimTranscript.textContent = text;
        return;
    }
    
    interimTranscript.textContent = '';
    
    const message = document.createElement('div');
    message.className = `message ${speaker}`;
    
    const now = new Date();
    const time = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    
    const avatarIcon = speaker === 'ai' 
        ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2a2 2 0 012 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 017 7h1a1 1 0 011 1v3a1 1 0 01-1 1h-1v1a2 2 0 01-2 2H5a2 2 0 01-2-2v-1H2a1 1 0 01-1-1v-3a1 1 0 011-1h1a7 7 0 017-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 012-2z"/></svg>'
        : '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>';
    
    const senderName = speaker === 'ai' ? 'AI Interviewer' : 'You';
    
    message.innerHTML = `
        <div class="message-avatar">${avatarIcon}</div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-sender">${senderName}</span>
                <span class="message-time">${time}</span>
            </div>
            <div class="message-bubble">${text}</div>
        </div>
    `;
    
    transcript.appendChild(message);
    transcriptContainer.scrollTop = transcriptContainer.scrollHeight;
}

function clearTranscript() {
    transcript.innerHTML = '';
    interimTranscript.textContent = '';
    transcriptPlaceholder.classList.remove('hidden');
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
            updateConnectionStatus(true, 'Connected');
            resolve();
        };
        
        websocket.onclose = (event) => {
            console.log('🔌 WebSocket closed:', event.code, event.reason);
            updateConnectionStatus(false, 'Disconnected');
            if (isInterviewActive) {
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
            updateConnectionStatus(true, 'AI Connected');
            interruptBtn.disabled = false;
            break;
            
        case 'audio':
            handleGeminiAudio(data.data);
            break;
            
        case 'transcript':
            if (data.text) {
                appendTranscript(data.text, 'ai');
            }
            break;
            
        case 'text':
            appendTranscript(data.data, 'ai');
            break;
            
        case 'interrupted':
            console.log('🛑 AI interrupted');
            if (audioStreamer) {
                audioStreamer.interrupt();
            }
            isAISpeaking = false;
            updateAIStatus(true, false, 'Listening');
            break;
            
        case 'turn_complete':
            console.log('✅ AI turn complete');
            isAISpeaking = false;
            updateAIStatus(true, false, 'Your Turn');
            if (audioStreamer) {
                audioStreamer.resetBuffering();
            }
            break;
            
        case 'error':
            console.error('❌ Server error:', data.message);
            showError(data.message || 'Server error occurred');
            break;
    }
}

function handleGeminiAudio(base64Data) {
    if (!audioStreamer) return;
    
    const originalSamples = audioStreamer.addChunk(base64Data);
    
    if (originalSamples) {
        isAISpeaking = true;
        updateAIStatus(true, true, 'Speaking...');
    }
}

function handleMicrophoneAudio(int16Data, rms) {
    if (!isInterviewActive || !websocket || websocket.readyState !== WebSocket.OPEN) return;
    
    updateAudioLevel(rms);
    
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
        hideError();
        
        // Start camera
        const cameraStarted = await startCamera();
        if (!cameraStarted) {
            startBtn.disabled = false;
            return;
        }
        
        // Initialize audio streamer
        audioStreamer = new AudioStreamer();
        await audioStreamer.initialize();
        
        // Connect WebSocket
        await connectWebSocket();
        
        // Initialize audio recorder
        audioRecorder = new AudioRecorder(handleMicrophoneAudio);
        await audioRecorder.start();
        updateMicStatus(true, 'Mic Live');
        
        isInterviewActive = true;
        stopBtn.disabled = false;
        
        // Start timer
        startTimer();
        
        // Clear previous transcript
        clearTranscript();
        
        console.log('🎙️ Interview started');
        
    } catch (error) {
        console.error('❌ Error starting interview:', error);
        
        if (error.name === 'NotAllowedError') {
            showError('Microphone access denied. Please allow microphone permissions.');
        } else {
            showError('Failed to start interview. Please check permissions and try again.');
        }
        
        startBtn.disabled = false;
        stopCamera();
        stopTimer();
    }
}

async function interruptAI() {
    if (!isInterviewActive) return;
    
    console.log('✋ User requested interrupt');
    
    if (audioStreamer) {
        await audioStreamer.interrupt();
    }
    
    if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.send(JSON.stringify({ type: 'interrupt' }));
    }
    
    isAISpeaking = false;
    updateAIStatus(true, false, 'Interrupted');
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
    
    // Stop camera
    stopCamera();
    
    // Stop timer
    stopTimer();
    
    // Update UI
    startBtn.disabled = false;
    stopBtn.disabled = true;
    interruptBtn.disabled = true;
    updateMicStatus(false, 'Mic Ready');
    updateConnectionStatus(false, 'Disconnected');
    updateAIStatus(false, false, 'AI Ready');
    isAISpeaking = false;
    
    console.log('🏁 Interview stopped');
}

// ======================================================================
// INITIALIZATION
// ======================================================================

document.addEventListener('DOMContentLoaded', async () => {
    // Language badge click handlers
    languageBadges.forEach(badge => {
        badge.addEventListener('click', () => {
            languageBadges.forEach(b => b.classList.remove('active'));
            badge.classList.add('active');
        });
    });
    
    // Camera selection event listeners
    if (cameraSelect) {
        cameraSelect.addEventListener('change', handleCameraChange);
    }
    
    if (refreshCamerasBtn) {
        refreshCamerasBtn.addEventListener('click', refreshCameraList);
    }
    
    // Populate camera dropdown on page load
    await populateCameraDropdown();
    
    // Listen for device changes (camera plugged/unplugged)
    navigator.mediaDevices.addEventListener('devicechange', async () => {
        console.log('📷 Device change detected, refreshing camera list...');
        await populateCameraDropdown();
    });
    
    console.log('🚀 Live AI Interview Platform initialized');
    console.log('📝 Supported languages: English, Hindi (हिंदी), Gujarati (ગુજરાતી)');
    console.log('📷 Camera selection enabled');
});

// Handle page unload
window.addEventListener('beforeunload', () => {
    if (isInterviewActive) {
        stopInterview();
    }
});

