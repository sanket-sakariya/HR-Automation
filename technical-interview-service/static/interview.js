/**
 * Technical Interview Service - Frontend JavaScript
 * Handles WebSocket communication, audio streaming, and UI interactions
 */

// Audio settings
const AUDIO_SAMPLE_RATE = 16000;
const PLAYBACK_SAMPLE_RATE = 24000;

// State
let sessionId = null;
let technicalInterviewId = null;
let ws = null;
let audioContext = null;
let mediaStream = null;
let audioWorklet = null;
let isRecording = false;
let isMicMuted = false;
let isCameraOff = false;
let interviewStartTime = null;
let timerInterval = null;
let audioQueue = [];
let isPlaying = false;

// Speech Recognition for user transcript
let speechRecognition = null;
let recognitionActive = false;

// DOM Elements
const loginContainer = document.getElementById('loginContainer');
const interviewContainer = document.getElementById('interviewContainer');
const loadingScreen = document.getElementById('loadingScreen');
const loadingText = document.getElementById('loadingText');
const errorMessage = document.getElementById('errorMessage');
const loginForm = document.getElementById('loginForm');
const loginBtn = document.getElementById('loginBtn');
const transcriptBody = document.getElementById('transcriptBody');
const timerDisplay = document.getElementById('timerDisplay');
const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const aiAvatar = document.getElementById('aiAvatar');
const userVideo = document.getElementById('userVideo');
const micBtn = document.getElementById('micBtn');
const cameraBtn = document.getElementById('cameraBtn');
const permissionModal = document.getElementById('permissionModal');

// Store job requirement ID from URL
let jobRequirementId = null;

// Check for URL parameters (session or job from link)
function checkUrlParams() {
    const urlParams = new URLSearchParams(window.location.search);
    const urlSessionId = urlParams.get('session');
    const urlJobId = urlParams.get('job');
    
    // If session ID is provided, go directly to interview
    if (urlSessionId) {
        sessionId = urlSessionId;
        showLoading('Loading interview session...');
        validateAndStartSession(urlSessionId);
        return;
    }
    
    // Check path for session ID (e.g., /interview/TI-xxx)
    const pathMatch = window.location.pathname.match(/\/interview\/([^/]+)/);
    if (pathMatch) {
        sessionId = pathMatch[1];
        showLoading('Loading interview session...');
        validateAndStartSession(sessionId);
        return;
    }
    
    // If job ID is provided, show login form
    if (urlJobId) {
        jobRequirementId = urlJobId;
        document.getElementById('jobId').value = urlJobId;
        document.getElementById('loginForm').style.display = 'block';
        document.getElementById('noJobError').style.display = 'none';
        
        // Optionally fetch job details to show title
        fetchJobDetails(urlJobId);
    } else {
        // No job ID - show error
        document.getElementById('loginForm').style.display = 'none';
        document.getElementById('noJobError').style.display = 'block';
    }
}

// Fetch job details to display job title
async function fetchJobDetails(jobId) {
    try {
        // Try to get job title from main service (optional)
        const response = await fetch(`http://localhost:8888/interview-management-service/api/v1/job-requirements/${jobId}`);
        if (response.ok) {
            const data = await response.json();
            if (data.data && data.data.title) {
                document.getElementById('jobTitleDisplay').textContent = data.data.title;
                document.getElementById('jobInfo').style.display = 'block';
            }
        }
    } catch (error) {
        // Silently fail - job title is optional UI enhancement
        console.log('Could not fetch job details:', error);
    }
}

// Validate and start session
async function validateAndStartSession(sid) {
    try {
        const response = await fetch(`/api/session/${sid}`);
        if (!response.ok) {
            throw new Error('Invalid session');
        }
        
        const data = await response.json();
        if (data.success) {
            technicalInterviewId = data.technical_interview_id;
            
            // Update UI
            document.getElementById('jobTitle').textContent = data.job_details?.title || 'Technical Interview';
            document.getElementById('candidateName').textContent = 
                `Welcome, ${data.candidate_info?.first_name || ''} ${data.candidate_info?.last_name || ''}`.trim() || 'Welcome, Candidate';
            
            hideLoading();
            showPermissionModal();
        } else {
            throw new Error('Session validation failed');
        }
    } catch (error) {
        console.error('Session validation error:', error);
        hideLoading();
        showError('Invalid or expired interview session. Please login again.');
        loginContainer.classList.remove('hidden');
    }
}

// Login Form Handler
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const jobId = document.getElementById('jobId').value.trim() || jobRequirementId;
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    
    if (!jobId) {
        showError('Invalid interview link. Please use the link provided by the recruiter.');
        return;
    }
    
    if (!email || !password) {
        showError('Please enter your email and password');
        return;
    }
    
    loginBtn.disabled = true;
    loginBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Logging in...';
    hideError();
    
    try {
        const response = await fetch(`/api/login/${jobId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Login failed');
        }
        
        if (data.success) {
            sessionId = data.session_id;
            technicalInterviewId = data.technical_interview_id;
            
            // Update UI
            document.getElementById('jobTitle').textContent = data.job_details?.title || 'Technical Interview';
            document.getElementById('candidateName').textContent = 
                `Welcome, ${data.candidate_info?.first_name || ''} ${data.candidate_info?.last_name || ''}`.trim() || 'Welcome, Candidate';
            
            // Show permission modal
            loginContainer.classList.add('hidden');
            showPermissionModal();
        } else {
            throw new Error('Login failed');
        }
    } catch (error) {
        console.error('Login error:', error);
        showError(error.message);
    } finally {
        loginBtn.disabled = false;
        loginBtn.innerHTML = '<i class="fas fa-sign-in-alt"></i> Start Interview';
    }
});

// Show/Hide helpers
function showLoading(text = 'Loading...') {
    loadingText.textContent = text;
    loadingScreen.classList.remove('hidden');
}

function hideLoading() {
    loadingScreen.classList.add('hidden');
}

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
}

function hideError() {
    errorMessage.style.display = 'none';
}

function showPermissionModal() {
    permissionModal.classList.add('active');
}

function hidePermissionModal() {
    permissionModal.classList.remove('active');
}

// Request microphone and camera permissions
async function requestPermissions() {
    hidePermissionModal();
    showLoading('Requesting permissions...');
    
    try {
        mediaStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                sampleRate: AUDIO_SAMPLE_RATE,
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
            },
            video: true
        });
        
        // Show video preview
        userVideo.srcObject = mediaStream;
        
        // Start interview
        await startInterview();
    } catch (error) {
        console.error('Permission error:', error);
        hideLoading();
        alert('Microphone access is required for the interview. Please allow permissions and try again.');
        showPermissionModal();
    }
}

// Start Interview
async function startInterview() {
    showLoading('Connecting to AI interviewer...');
    
    try {
        // Initialize Speech Recognition for user transcript
        initSpeechRecognition();
        
        // Initialize Audio Context
        audioContext = new (window.AudioContext || window.webkitAudioContext)({
            sampleRate: AUDIO_SAMPLE_RATE
        });
        
        // Resume audio context (required by some browsers)
        if (audioContext.state === 'suspended') {
            await audioContext.resume();
        }
        
        // Load audio worklet for capturing audio
        await loadAudioWorklet();
        
        // Connect WebSocket
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/ws/${sessionId}`;
        
        console.log('Connecting to WebSocket:', wsUrl);
        ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
            console.log('WebSocket connected');
            updateStatus('connected', 'Connected to AI');
        };
        
        ws.onmessage = (event) => {
            handleWebSocketMessage(JSON.parse(event.data));
        };
        
        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            updateStatus('disconnected', 'Connection error');
        };
        
        ws.onclose = () => {
            console.log('WebSocket closed');
            updateStatus('disconnected', 'Disconnected');
            stopRecording();
        };
        
    } catch (error) {
        console.error('Start interview error:', error);
        hideLoading();
        alert('Failed to start interview: ' + error.message);
    }
}

// Load Audio Worklet for capturing audio
async function loadAudioWorklet() {
    // Create audio worklet processor inline
    const workletCode = `
        class AudioProcessor extends AudioWorkletProcessor {
            constructor() {
                super();
                this.bufferSize = 2048;
                this.buffer = new Float32Array(this.bufferSize);
                this.bufferIndex = 0;
            }
            
            process(inputs) {
                const input = inputs[0];
                if (input.length > 0) {
                    const channelData = input[0];
                    
                    for (let i = 0; i < channelData.length; i++) {
                        this.buffer[this.bufferIndex++] = channelData[i];
                        
                        if (this.bufferIndex >= this.bufferSize) {
                            // Convert to 16-bit PCM
                            const pcmData = new Int16Array(this.bufferSize);
                            for (let j = 0; j < this.bufferSize; j++) {
                                const s = Math.max(-1, Math.min(1, this.buffer[j]));
                                pcmData[j] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                            }
                            
                            this.port.postMessage(pcmData.buffer);
                            this.bufferIndex = 0;
                        }
                    }
                }
                return true;
            }
        }
        registerProcessor('audio-processor', AudioProcessor);
    `;
    
    const blob = new Blob([workletCode], { type: 'application/javascript' });
    const workletUrl = URL.createObjectURL(blob);
    
    await audioContext.audioWorklet.addModule(workletUrl);
    
    // Create audio source from microphone
    const source = audioContext.createMediaStreamSource(mediaStream);
    
    // Create worklet node
    audioWorklet = new AudioWorkletNode(audioContext, 'audio-processor');
    
    // Handle audio data from worklet
    audioWorklet.port.onmessage = (event) => {
        if (isRecording && ws && ws.readyState === WebSocket.OPEN && !isMicMuted) {
            const audioData = new Uint8Array(event.data);
            const base64Audio = arrayBufferToBase64(audioData);
            
            ws.send(JSON.stringify({
                type: 'audio',
                data: base64Audio
            }));
        }
    };
    
    // Connect source to worklet
    source.connect(audioWorklet);
}

// Handle WebSocket messages
function handleWebSocketMessage(message) {
    switch (message.type) {
        case 'setup_complete':
            console.log('AI setup complete');
            hideLoading();
            loginContainer.classList.add('hidden');
            interviewContainer.style.display = 'block';
            startTimer();
            startRecording();
            updateStatus('connected', 'Interview in progress');
            break;
            
        case 'audio':
            // Play audio from AI
            playAudio(message.data, message.mimeType);
            aiAvatar.classList.add('speaking');
            break;
            
        case 'turn_complete':
            console.log('AI turn complete');
            aiAvatar.classList.remove('speaking');
            break;
            
        case 'interrupted':
            console.log('AI interrupted');
            aiAvatar.classList.remove('speaking');
            clearAudioQueue();
            break;
            
        case 'transcript':
            addTranscriptMessage(message.text, message.speaker);
            break;
            
        case 'error':
            console.error('Server error:', message.message);
            updateStatus('disconnected', 'Error: ' + message.message);
            break;
    }
}

// Audio playback
function playAudio(base64Data, mimeType) {
    try {
        const audioData = base64ToArrayBuffer(base64Data);
        audioQueue.push(audioData);
        
        if (!isPlaying) {
            playNextInQueue();
        }
    } catch (error) {
        console.error('Error queuing audio:', error);
    }
}

async function playNextInQueue() {
    if (audioQueue.length === 0) {
        isPlaying = false;
        return;
    }
    
    isPlaying = true;
    const audioData = audioQueue.shift();
    
    try {
        // Create playback context with higher sample rate
        const playbackContext = new (window.AudioContext || window.webkitAudioContext)({
            sampleRate: PLAYBACK_SAMPLE_RATE
        });
        
        // Convert raw PCM to audio buffer
        const int16Data = new Int16Array(audioData);
        const float32Data = new Float32Array(int16Data.length);
        
        for (let i = 0; i < int16Data.length; i++) {
            float32Data[i] = int16Data[i] / 32768.0;
        }
        
        const audioBuffer = playbackContext.createBuffer(1, float32Data.length, PLAYBACK_SAMPLE_RATE);
        audioBuffer.getChannelData(0).set(float32Data);
        
        const source = playbackContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(playbackContext.destination);
        
        source.onended = () => {
            playbackContext.close();
            playNextInQueue();
        };
        
        source.start(0);
    } catch (error) {
        console.error('Error playing audio:', error);
        playNextInQueue();
    }
}

function clearAudioQueue() {
    audioQueue = [];
    isPlaying = false;
}

// Initialize Speech Recognition for user transcript
function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        console.warn('Speech Recognition not supported in this browser');
        return;
    }
    
    speechRecognition = new SpeechRecognition();
    speechRecognition.continuous = true;
    speechRecognition.interimResults = false;
    speechRecognition.lang = 'en-IN'; // English India - also understands Hindi
    
    speechRecognition.onresult = (event) => {
        for (let i = event.resultIndex; i < event.results.length; i++) {
            if (event.results[i].isFinal) {
                const transcript = event.results[i][0].transcript.trim();
                if (transcript) {
                    console.log('User said:', transcript);
                    // Add to UI
                    addTranscriptMessage(transcript, 'candidate');
                    // Send to server for storage
                    if (ws && ws.readyState === WebSocket.OPEN) {
                        ws.send(JSON.stringify({
                            type: 'transcript',
                            text: transcript,
                            speaker: 'candidate'
                        }));
                    }
                }
            }
        }
    };
    
    speechRecognition.onerror = (event) => {
        console.warn('Speech recognition error:', event.error);
        // Restart on recoverable errors
        if (event.error === 'no-speech' || event.error === 'audio-capture') {
            if (recognitionActive && isRecording) {
                setTimeout(() => {
                    try { speechRecognition.start(); } catch(e) {}
                }, 100);
            }
        }
    };
    
    speechRecognition.onend = () => {
        // Auto-restart if still recording
        if (recognitionActive && isRecording && !isMicMuted) {
            try { speechRecognition.start(); } catch(e) {}
        }
    };
}

// Recording controls
function startRecording() {
    isRecording = true;
    console.log('Recording started');
    
    // Start speech recognition for transcript
    if (speechRecognition) {
        recognitionActive = true;
        try { speechRecognition.start(); } catch(e) {}
    }
}

function stopRecording() {
    isRecording = false;
    recognitionActive = false;
    console.log('Recording stopped');
    
    // Stop speech recognition
    if (speechRecognition) {
        try { speechRecognition.stop(); } catch(e) {}
    }
}

// Microphone toggle
function toggleMic() {
    isMicMuted = !isMicMuted;
    
    if (mediaStream) {
        mediaStream.getAudioTracks().forEach(track => {
            track.enabled = !isMicMuted;
        });
    }
    
    micBtn.classList.toggle('muted', isMicMuted);
    micBtn.innerHTML = isMicMuted 
        ? '<i class="fas fa-microphone-slash"></i>' 
        : '<i class="fas fa-microphone"></i>';
}

// Camera toggle
function toggleCamera() {
    isCameraOff = !isCameraOff;
    
    if (mediaStream) {
        mediaStream.getVideoTracks().forEach(track => {
            track.enabled = !isCameraOff;
        });
    }
    
    cameraBtn.classList.toggle('off', isCameraOff);
    cameraBtn.innerHTML = isCameraOff 
        ? '<i class="fas fa-video-slash"></i>' 
        : '<i class="fas fa-video"></i>';
}

// End interview
function endInterview() {
    if (confirm('Are you sure you want to end the interview?')) {
        stopRecording();
        clearAudioQueue();
        
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'stop' }));
            ws.close();
        }
        
        if (mediaStream) {
            mediaStream.getTracks().forEach(track => track.stop());
        }
        
        if (audioContext) {
            audioContext.close();
        }
        
        stopTimer();
        
        // Show completion message
        interviewContainer.innerHTML = `
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; text-align: center;">
                <i class="fas fa-check-circle" style="font-size: 80px; color: #22c55e; margin-bottom: 30px;"></i>
                <h1 style="font-size: 32px; margin-bottom: 15px;">Interview Completed!</h1>
                <p style="color: #94a3b8; font-size: 18px; max-width: 500px; line-height: 1.6;">
                    Thank you for completing your technical interview. Your responses have been recorded and will be reviewed by our team.
                </p>
                <p style="color: #94a3b8; font-size: 16px; margin-top: 20px;">
                    Interview Duration: <strong>${timerDisplay.textContent}</strong>
                </p>
                <button onclick="window.close()" class="btn btn-primary" style="margin-top: 30px; max-width: 200px;">
                    Close Window
                </button>
            </div>
        `;
    }
}

// Timer
function startTimer() {
    interviewStartTime = Date.now();
    timerInterval = setInterval(updateTimer, 1000);
}

function updateTimer() {
    if (!interviewStartTime) return;
    
    const elapsed = Math.floor((Date.now() - interviewStartTime) / 1000);
    const hours = Math.floor(elapsed / 3600);
    const minutes = Math.floor((elapsed % 3600) / 60);
    const seconds = elapsed % 60;
    
    timerDisplay.textContent = 
        `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
}

// Status updates
function updateStatus(status, text) {
    statusDot.className = 'status-dot ' + status;
    statusText.textContent = text;
}

// Transcript
function addTranscriptMessage(text, speaker) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `transcript-message ${speaker === 'ai' ? 'ai' : 'user'}`;
    
    const labelIcon = speaker === 'ai' ? 'robot' : 'user';
    const labelText = speaker === 'ai' ? 'AI Interviewer' : 'You';
    
    messageDiv.innerHTML = `
        <span class="message-label">
            <i class="fas fa-${labelIcon}"></i>
            ${labelText}
        </span>
        <div class="message-content">${escapeHtml(text)}</div>
    `;
    
    transcriptBody.appendChild(messageDiv);
    transcriptBody.scrollTop = transcriptBody.scrollHeight;
}

// Utility functions
function arrayBufferToBase64(buffer) {
    let binary = '';
    const bytes = new Uint8Array(buffer);
    for (let i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
}

function base64ToArrayBuffer(base64) {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    checkUrlParams();
});
