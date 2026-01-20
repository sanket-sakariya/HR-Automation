/**
 * Real-time Multilingual AI Interviewer - Frontend Application
 * 
 * Features:
 * - WebSocket communication with FastAPI backend → Gemini 2.5 Flash
 * - AudioWorklet-based audio capture (16kHz PCM mono)
 * - AudioWorklet-based audio playback (24kHz PCM) - click-free
 * - Barge-in/interruption handling
 * - Multilingual support: English, Hindi, Gujarati
 * - Real-time audio visualization
 */

// ============== Configuration ==============
const SAMPLE_RATE_INPUT = 16000;   // Microphone: 16kHz
const SAMPLE_RATE_OUTPUT = 24000;  // Gemini output: 24kHz
const NUM_VISUALIZER_BARS = 32;
const CAPTURE_CHUNK_SIZE = 2048;   // Samples per chunk to send

// ============== State ==============
let websocket = null;
let audioContext = null;
let captureContext = null;
let mediaStream = null;
let captureWorklet = null;
let playbackWorklet = null;
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

// ============== Initialize Visualizer ==============
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

// ============== Status Updates ==============
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
    
    // Update language badges
    languageBadges.forEach(badge => {
        badge.classList.remove('active');
        if (badge.dataset.lang === langCode || 
            badge.dataset.lang === lang.toLowerCase().substring(0, 2)) {
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

// ============== WebSocket Communication ==============
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
    console.log('📨 Server message:', data.type, data.type === 'audio' ? `(${data.data?.length} chars)` : '');
    
    switch (data.type) {
        case 'setup_complete':
            console.log('✅ Gemini setup complete');
            setStatus('user-speaking', 'Listening... Speak in any language!');
            interruptBtn.disabled = false;
            break;
            
        case 'audio':
            // Send audio to playback worklet
            handleAudioData(data.data);
            break;
            
        case 'transcript':
            // AI's spoken text
            if (data.text) {
                appendTranscript(data.text, 'ai', data.language);
                if (data.language) {
                    updateDetectedLanguage(data.language);
                }
            }
            break;
            
        case 'text':
            // Legacy text response
            appendTranscript(data.data, 'ai');
            break;
            
        case 'interrupted':
            // Barge-in: stop current playback immediately
            console.log('🛑 AI interrupted - clearing playback');
            clearPlaybackBuffer();
            isAISpeaking = false;
            setStatus('user-speaking', 'Listening...');
            visualizerLabel.textContent = 'Your Audio';
            break;
            
        case 'turn_complete':
            console.log('✅ AI turn complete');
            isAISpeaking = false;
            setStatus('user-speaking', 'Your turn - Speak now');
            visualizerLabel.textContent = 'Your Audio';
            break;
            
        case 'error':
            console.error('❌ Server error:', data.message);
            showError(data.message || 'Server error occurred');
            break;
            
        default:
            console.log('📨 Unknown message type:', data.type, data);
    }
}

// ============== AudioWorklet-based Audio Capture ==============
async function startAudioCapture() {
    try {
        // Request microphone access
        mediaStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                sampleRate: SAMPLE_RATE_INPUT,
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
            }
        });
        
        // Create audio context for capture at 16kHz
        captureContext = new AudioContext({ sampleRate: SAMPLE_RATE_INPUT });
        
        // Load capture worklet
        await captureContext.audioWorklet.addModule('/static/capture-worklet.js');
        
        // Create capture worklet node
        captureWorklet = new AudioWorkletNode(captureContext, 'capture-processor', {
            processorOptions: { chunkSize: CAPTURE_CHUNK_SIZE }
        });
        
        // Handle audio chunks from worklet
        captureWorklet.port.onmessage = (event) => {
            if (!isInterviewActive || !websocket || websocket.readyState !== WebSocket.OPEN) {
                return;
            }
            
            const { pcmData, levels } = event.data;
            
            // Calculate average level from levels array
            const level = levels ? levels.reduce((a, b) => a + b, 0) / levels.length : 0;
            
            // Send PCM audio to server (base64 encoded)
            const base64Data = arrayBufferToBase64(pcmData);
            websocket.send(JSON.stringify({
                type: 'audio',
                data: base64Data
            }));
            
            // Update input meter
            updateAudioMeter(level);
            
            // Update visualizer when user is speaking (not AI)
            if (!isAISpeaking && level > 0.01) {
                // Use actual mic levels for visualization
                const vizData = Array(NUM_VISUALIZER_BARS).fill(0).map((_, i) => {
                    const levelIdx = Math.floor(i * levels.length / NUM_VISUALIZER_BARS);
                    return (levels[levelIdx] || 0) * 2.5;
                });
                updateVisualizer(vizData);
            }
        };
        
        // Connect microphone → capture worklet
        const source = captureContext.createMediaStreamSource(mediaStream);
        source.connect(captureWorklet);
        
        console.log('🎤 Audio capture started (AudioWorklet, 16kHz)');
        
    } catch (error) {
        console.error('❌ Error starting audio capture:', error);
        throw error;
    }
}

function stopAudioCapture() {
    if (captureWorklet) {
        captureWorklet.disconnect();
        captureWorklet = null;
    }
    
    if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop());
        mediaStream = null;
    }
    
    if (captureContext && captureContext.state !== 'closed') {
        captureContext.close();
        captureContext = null;
    }
    
    resetVisualizer();
    console.log('🎤 Audio capture stopped');
}

// ============== AudioWorklet-based Audio Playback ==============
async function initPlaybackWorklet() {
    // Create audio context for playback at 24kHz
    audioContext = new AudioContext({ sampleRate: SAMPLE_RATE_OUTPUT });
    
    // Resume context immediately (user has clicked start button)
    if (audioContext.state === 'suspended') {
        await audioContext.resume();
        console.log('🔊 AudioContext resumed');
    }
    
    try {
        // Load playback worklet
        await audioContext.audioWorklet.addModule('/static/playback-worklet.js');
        
        // Create playback worklet node
        playbackWorklet = new AudioWorkletNode(audioContext, 'playback-processor');
        
        // Handle messages from playback worklet (for visualization)
        playbackWorklet.port.onmessage = (event) => {
            const data = event.data;
            
            if (data.type === 'levels' && data.levels && isAISpeaking) {
                // Use actual audio levels from worklet for visualization
                const levels = data.levels;
                const maxLevel = Math.max(...levels);
                
                // Create visualization from audio levels
                const vizData = Array(NUM_VISUALIZER_BARS).fill(0).map((_, i) => {
                    const levelIndex = Math.floor(i * levels.length / NUM_VISUALIZER_BARS);
                    const level = levels[levelIndex] || 0;
                    const variation = Math.sin(Date.now() / 80 + i * 0.4) * 0.15;
                    return Math.max(0, (level * 3) + variation);
                });
                updateVisualizer(vizData);
            }
        };
        
        // Connect worklet to speakers
        playbackWorklet.connect(audioContext.destination);
        
        console.log('🔊 Playback worklet initialized (24kHz)');
    } catch (error) {
        console.warn('⚠️ AudioWorklet not supported, using fallback:', error);
        playbackWorklet = null; // Will use fallback playback
    }
}

function handleAudioData(base64Data) {
    console.log('🔊 handleAudioData called, base64 length:', base64Data.length);
    
    // Decode base64 to ArrayBuffer (Int16 PCM)
    const binaryString = atob(base64Data);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
    }
    
    // Convert Int16 PCM to Float32 (required by Web Audio API)
    const int16Array = new Int16Array(bytes.buffer);
    const float32Array = new Float32Array(int16Array.length);
    for (let i = 0; i < int16Array.length; i++) {
        float32Array[i] = int16Array[i] / 32768.0;
    }
    
    console.log('🔊 Decoded audio samples:', float32Array.length);
    
    // Copy array for visualization before potential transfer
    const vizSamples = new Float32Array(float32Array);
    
    // Try playback worklet first, fall back to simple playback
    if (playbackWorklet) {
        // Send a copy to worklet (don't transfer - we need it for viz)
        playbackWorklet.port.postMessage({
            type: 'audio',
            samples: new Float32Array(float32Array)
        });
    } else {
        // Fallback: direct playback using AudioBuffer
        playAudioDirect(new Float32Array(float32Array));
    }
    
    isAISpeaking = true;
    setStatus('ai-speaking', 'AI is speaking...');
    visualizerLabel.textContent = 'AI Audio';
    
    // Animate visualizer based on audio samples
    animateVisualizerForAudio(vizSamples);
}

// Fallback direct playback without worklet
function playAudioDirect(float32Array) {
    if (!audioContext || audioContext.state === 'closed') {
        audioContext = new AudioContext({ sampleRate: SAMPLE_RATE_OUTPUT });
    }
    
    // Resume if suspended (browser autoplay policy)
    if (audioContext.state === 'suspended') {
        audioContext.resume();
    }
    
    const audioBuffer = audioContext.createBuffer(1, float32Array.length, SAMPLE_RATE_OUTPUT);
    audioBuffer.getChannelData(0).set(float32Array);
    
    const source = audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioContext.destination);
    source.start();
    
    console.log('🔊 Playing audio direct:', float32Array.length, 'samples');
}

// Animate visualizer based on audio samples
function animateVisualizerForAudio(samples) {
    // Calculate RMS level from samples if available
    let rms = 0.3; // Default moderate level
    
    if (samples && samples.length > 0) {
        let sum = 0;
        for (let i = 0; i < samples.length; i++) {
            sum += samples[i] * samples[i];
        }
        rms = Math.sqrt(sum / samples.length);
    }
    
    // Create visualization based on RMS
    const vizData = Array(NUM_VISUALIZER_BARS).fill(0).map((_, i) => {
        const phase = Date.now() / 80 + i * 0.35;
        const wave = Math.sin(phase) * 0.3 + Math.cos(phase * 0.7) * 0.2;
        return Math.max(0.08, (rms * 5) + wave * 0.5);
    });
    updateVisualizer(vizData);
}

function clearPlaybackBuffer() {
    if (playbackWorklet) {
        playbackWorklet.port.postMessage({ type: 'clear' });
    }
    resetVisualizer();
}

function stopAudioPlayback() {
    clearPlaybackBuffer();
    
    if (playbackWorklet) {
        playbackWorklet.disconnect();
        playbackWorklet = null;
    }
    
    if (audioContext && audioContext.state !== 'closed') {
        audioContext.close();
        audioContext = null;
    }
    
    isAISpeaking = false;
    resetVisualizer();
    console.log('🔊 Audio playback stopped');
}

// ============== Utility Functions ==============
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

// ============== Interview Control ==============
async function startInterview() {
    try {
        startBtn.disabled = true;
        interruptBtn.disabled = true;
        setStatus('', 'Connecting...');
        
        // Initialize visualizer
        initVisualizer();
        
        // Initialize playback worklet first
        await initPlaybackWorklet();
        
        // Connect WebSocket
        await connectWebSocket();
        
        // Start audio capture
        await startAudioCapture();
        
        isInterviewActive = true;
        stopBtn.disabled = false;
        
        // Clear previous transcript
        clearTranscript();
        
        // Reset language detection
        detectedLanguageEl.style.display = 'none';
        
        console.log('🎙️ Interview started');
        
    } catch (error) {
        console.error('❌ Error starting interview:', error);
        showError('Failed to start interview. Please check microphone permissions.');
        setStatus('', 'Error - Click Start to retry');
        startBtn.disabled = false;
        interruptBtn.disabled = true;
    }
}

function interruptAI() {
    if (!isInterviewActive) return;
    
    console.log('✋ User requested interrupt');
    
    // Send interrupt signal to server
    if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.send(JSON.stringify({ type: 'interrupt' }));
    }
    
    // Clear local playback immediately
    clearPlaybackBuffer();
    isAISpeaking = false;
    setStatus('user-speaking', 'Listening...');
    visualizerLabel.textContent = 'Your Audio';
}

function stopInterview() {
    isInterviewActive = false;
    
    // Send stop signal
    if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.send(JSON.stringify({ type: 'stop' }));
        websocket.close();
    }
    websocket = null;
    
    // Stop audio
    stopAudioCapture();
    stopAudioPlayback();
    
    // Update UI
    startBtn.disabled = false;
    stopBtn.disabled = true;
    interruptBtn.disabled = true;
    setStatus('', 'Interview ended');
    resetVisualizer();
    detectedLanguageEl.style.display = 'none';
    
    console.log('🏁 Interview stopped');
}

// ============== Initialize ==============
document.addEventListener('DOMContentLoaded', () => {
    initVisualizer();
    
    // Language badge click handlers (informational only)
    languageBadges.forEach(badge => {
        badge.addEventListener('click', () => {
            // Just visual feedback - actual language is auto-detected
            languageBadges.forEach(b => b.classList.remove('active'));
            badge.classList.add('active');
        });
    });
    
    console.log('🚀 Multilingual AI Interviewer ready');
    console.log('📝 Supported languages: English, Hindi (हिंदी), Gujarati (ગુજરાતી)');
});

// Handle page unload
window.addEventListener('beforeunload', () => {
    if (isInterviewActive) {
        stopInterview();
    }
});
