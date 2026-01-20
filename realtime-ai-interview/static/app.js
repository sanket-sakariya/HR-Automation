/**
 * Real-time AI Interviewer - Frontend Application
 * 
 * Handles:
 * - WebSocket communication with backend
 * - Audio capture (16kHz PCM mono)
 * - Audio playback (24kHz PCM) with smooth buffering
 * - Barge-in/interruption handling
 * - Audio visualization
 */

// ============== Configuration ==============
const SAMPLE_RATE_INPUT = 16000;   // Input: 16kHz
const SAMPLE_RATE_OUTPUT = 24000;  // Output: 24kHz from Gemini
const BUFFER_SIZE = 4096;
const NUM_VISUALIZER_BARS = 32;

// ============== State ==============
let websocket = null;
let audioContext = null;
let mediaStream = null;
let scriptProcessor = null;
let isInterviewActive = false;
let isAISpeaking = false;

// Audio playback queue
let audioQueue = [];
let isPlaying = false;

// ============== DOM Elements ==============
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const statusIndicator = document.getElementById('statusIndicator');
const statusText = document.getElementById('statusText');
const transcript = document.getElementById('transcript');
const errorMessage = document.getElementById('errorMessage');
const audioVisualizer = document.getElementById('audioVisualizer');

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
    for (let i = 0; i < bars.length; i++) {
        const value = values[i] || 0;
        const height = Math.max(4, value * 80);
        bars[i].style.height = `${height}px`;
    }
}

function resetVisualizer() {
    const bars = audioVisualizer.children;
    for (let i = 0; i < bars.length; i++) {
        bars[i].style.height = '4px';
    }
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

function appendTranscript(text, speaker = 'ai') {
    const prefix = speaker === 'ai' ? '🤖 AI: ' : '👤 You: ';
    const entry = document.createElement('div');
    entry.style.marginBottom = '12px';
    entry.innerHTML = `<strong>${prefix}</strong>${text}`;
    transcript.appendChild(entry);
    transcript.scrollTop = transcript.scrollHeight;
}

// ============== WebSocket Communication ==============
function connectWebSocket() {
    return new Promise((resolve, reject) => {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        console.log('Connecting to WebSocket:', wsUrl);
        websocket = new WebSocket(wsUrl);
        
        websocket.onopen = () => {
            console.log('WebSocket connected');
            setStatus('connected', 'Connected - Setting up...');
            resolve();
        };
        
        websocket.onclose = (event) => {
            console.log('WebSocket closed:', event.code, event.reason);
            if (isInterviewActive) {
                setStatus('', 'Disconnected');
                stopInterview();
            }
        };
        
        websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
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
            console.log('Gemini setup complete');
            setStatus('listening', 'Listening... Speak now!');
            break;
            
        case 'audio':
            // Queue audio for playback
            handleAudioData(data.data);
            break;
            
        case 'text':
            // Display AI text response
            appendTranscript(data.data, 'ai');
            break;
            
        case 'interrupted':
            // Barge-in: stop current playback immediately
            console.log('AI interrupted - stopping playback');
            stopAudioPlayback();
            setStatus('listening', 'Listening...');
            break;
            
        case 'turn_complete':
            console.log('AI turn complete');
            isAISpeaking = false;
            setStatus('listening', 'Your turn - Speak now');
            break;
            
        default:
            console.log('Unknown message type:', data.type);
    }
}

// ============== Audio Capture ==============
async function startAudioCapture() {
    try {
        // Get microphone access
        mediaStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                sampleRate: SAMPLE_RATE_INPUT,
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
            }
        });
        
        // Create audio context
        audioContext = new (window.AudioContext || window.webkitAudioContext)({
            sampleRate: SAMPLE_RATE_INPUT
        });
        
        // Create source from microphone
        const source = audioContext.createMediaStreamSource(mediaStream);
        
        // Create script processor for raw PCM data
        scriptProcessor = audioContext.createScriptProcessor(BUFFER_SIZE, 1, 1);
        
        // Analyser for visualization
        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 64;
        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        
        scriptProcessor.onaudioprocess = (event) => {
            if (!isInterviewActive || !websocket || websocket.readyState !== WebSocket.OPEN) {
                return;
            }
            
            // Get raw PCM data
            const inputData = event.inputBuffer.getChannelData(0);
            
            // Convert Float32 to Int16 PCM
            const pcmData = float32ToInt16(inputData);
            
            // Convert to base64
            const base64Data = arrayBufferToBase64(pcmData.buffer);
            
            // Send to server
            websocket.send(JSON.stringify({
                type: 'audio',
                data: base64Data
            }));
            
            // Update visualizer
            analyser.getByteFrequencyData(dataArray);
            const normalizedData = Array.from(dataArray).map(v => v / 255);
            updateVisualizer(normalizedData);
        };
        
        // Connect audio nodes
        source.connect(analyser);
        source.connect(scriptProcessor);
        scriptProcessor.connect(audioContext.destination);
        
        console.log('Audio capture started');
        
    } catch (error) {
        console.error('Error starting audio capture:', error);
        throw error;
    }
}

function stopAudioCapture() {
    if (scriptProcessor) {
        scriptProcessor.disconnect();
        scriptProcessor = null;
    }
    
    if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop());
        mediaStream = null;
    }
    
    if (audioContext && audioContext.state !== 'closed') {
        audioContext.close();
        audioContext = null;
    }
    
    resetVisualizer();
    console.log('Audio capture stopped');
}

// ============== Audio Playback ==============
function handleAudioData(base64Data) {
    // Decode base64 to ArrayBuffer
    const binaryString = atob(base64Data);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
    }
    
    // Queue for playback
    audioQueue.push(bytes.buffer);
    
    if (!isPlaying) {
        playNextAudioChunk();
    }
    
    isAISpeaking = true;
    setStatus('speaking', 'AI is speaking...');
}

async function playNextAudioChunk() {
    if (audioQueue.length === 0) {
        isPlaying = false;
        return;
    }
    
    isPlaying = true;
    const arrayBuffer = audioQueue.shift();
    
    try {
        // Create audio context for playback if needed
        if (!audioContext || audioContext.state === 'closed') {
            audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: SAMPLE_RATE_OUTPUT
            });
        }
        
        // Convert Int16 PCM to Float32 for Web Audio API
        const int16Array = new Int16Array(arrayBuffer);
        const float32Array = new Float32Array(int16Array.length);
        
        for (let i = 0; i < int16Array.length; i++) {
            float32Array[i] = int16Array[i] / 32768.0;
        }
        
        // Create audio buffer
        const audioBuffer = audioContext.createBuffer(1, float32Array.length, SAMPLE_RATE_OUTPUT);
        audioBuffer.getChannelData(0).set(float32Array);
        
        // Create buffer source
        const source = audioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(audioContext.destination);
        
        // Play and handle completion
        source.onended = () => {
            playNextAudioChunk();
        };
        
        source.start();
        
        // Update visualizer during playback
        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 64;
        source.connect(analyser);
        
        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        const updateViz = () => {
            if (isAISpeaking) {
                analyser.getByteFrequencyData(dataArray);
                const normalizedData = Array.from(dataArray).map(v => v / 255);
                updateVisualizer(normalizedData);
                requestAnimationFrame(updateViz);
            }
        };
        updateViz();
        
    } catch (error) {
        console.error('Error playing audio:', error);
        playNextAudioChunk();
    }
}

function stopAudioPlayback() {
    audioQueue = [];
    isPlaying = false;
    isAISpeaking = false;
    resetVisualizer();
}

// ============== Utility Functions ==============
function float32ToInt16(float32Array) {
    const int16Array = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
        const s = Math.max(-1, Math.min(1, float32Array[i]));
        int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return int16Array;
}

function arrayBufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
}

// ============== Interview Control ==============
async function startInterview() {
    try {
        startBtn.disabled = true;
        setStatus('', 'Connecting...');
        
        // Initialize visualizer
        initVisualizer();
        
        // Connect WebSocket
        await connectWebSocket();
        
        // Start audio capture
        await startAudioCapture();
        
        isInterviewActive = true;
        stopBtn.disabled = false;
        
        // Clear previous transcript
        transcript.innerHTML = '';
        
        console.log('Interview started');
        
    } catch (error) {
        console.error('Error starting interview:', error);
        showError('Failed to start interview. Please check microphone permissions.');
        setStatus('', 'Error - Click Start to retry');
        startBtn.disabled = false;
    }
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
    setStatus('', 'Interview ended');
    resetVisualizer();
    
    console.log('Interview stopped');
}

// ============== Initialize ==============
document.addEventListener('DOMContentLoaded', () => {
    initVisualizer();
    console.log('AI Interviewer ready');
});

// Handle page unload
window.addEventListener('beforeunload', () => {
    if (isInterviewActive) {
        stopInterview();
    }
});
