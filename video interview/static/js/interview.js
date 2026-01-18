// Get DOM elements
let video = document.getElementById('video');
let statusDiv = document.getElementById('status');
let questionDiv = document.getElementById('question');
let transcriptDiv = document.getElementById('transcript-content');
let startBtn = document.getElementById('startBtn');
let stopBtn = document.getElementById('stopBtn');
let recordingIndicator = document.getElementById('recordingIndicator');
let cameraStatus = document.getElementById('cameraStatus');
let cameraModal = document.getElementById('cameraModal');
let cameraList = document.getElementById('cameraList');
let confirmCameraBtn = document.getElementById('confirmCameraBtn');

// State variables
let mediaStream = null;
let selectedLanguage = 'english';
let isInterviewActive = false;
let isProcessing = false;
let availableCameras = [];
let selectedDeviceId = null;

// Language selection
document.querySelectorAll('.language-option').forEach(option => {
    option.addEventListener('click', function() {
        if (isInterviewActive) {
            alert('Cannot change language during interview!');
            return;
        }
        document.querySelectorAll('.language-option').forEach(opt => {
            opt.classList.remove('selected');
        });
        this.classList.add('selected');
        selectedLanguage = this.getAttribute('data-lang');
        console.log('Selected language:', selectedLanguage);
    });
});

// Detect all available cameras
function detectCameras() {
    console.log('Detecting available cameras...');
    updateStatus('Detecting cameras...', 'processing');
    
    navigator.mediaDevices.enumerateDevices()
        .then(function(devices) {
            availableCameras = devices.filter(function(device) {
                return device.kind === 'videoinput';
            });
            
            console.log('Found ' + availableCameras.length + ' camera(s):');
            availableCameras.forEach(function(camera, index) {
                console.log((index + 1) + '. ' + camera.label + ' [' + camera.deviceId + ']');
            });
            
            if (availableCameras.length === 0) {
                updateStatus('No cameras detected! Please connect a camera.', 'processing');
                alert('No cameras found. Please connect a webcam and refresh the page.');
            } else if (availableCameras.length === 1) {
                // Auto-select if only one camera
                selectedDeviceId = availableCameras[0].deviceId;
                initCamera(selectedDeviceId);
            } else {
                // Show selection modal if multiple cameras
                updateStatus('Multiple cameras detected. Please select one.', 'ready');
                showCameraSelector();
            }
        })
        .catch(function(err) {
            console.error('Error detecting cameras:', err);
            updateStatus('Error detecting cameras. Check permissions.', 'processing');
        });
}

// Show camera selection modal
function showCameraSelector() {
    if (availableCameras.length === 0) {
        detectCameras();
        return;
    }
    
    cameraList.innerHTML = '';
    
    availableCameras.forEach(function(camera, index) {
        let option = document.createElement('div');
        option.className = 'camera-option-item';
        option.setAttribute('data-device-id', camera.deviceId);
        
        let label = camera.label || 'Camera ' + (index + 1);
        
        // Identify camera types
        let icon = '📹';
        if (label.toLowerCase().includes('usb')) {
            icon = '🔌';
        } else if (label.toLowerCase().includes('integrated') || label.toLowerCase().includes('built-in')) {
            icon = '💻';
        } else if (label.toLowerCase().includes('virtual')) {
            icon = '🖥️';
        }
        
        option.innerHTML = '<div class="camera-icon">' + icon + '</div>' +
            '<div class="camera-info">' +
            '<div class="camera-name">' + label + '</div>' +
            '<div class="camera-id">Device ID: ' + camera.deviceId.substring(0, 20) + '...</div>' +
            '</div>';
        
        option.onclick = function() {
            document.querySelectorAll('.camera-option-item').forEach(function(opt) {
                opt.classList.remove('selected');
            });
            option.classList.add('selected');
            selectedDeviceId = camera.deviceId;
            confirmCameraBtn.disabled = false;
        };
        
        cameraList.appendChild(option);
    });
    
    cameraModal.style.display = 'block';
    confirmCameraBtn.disabled = true;
}

// Confirm camera selection
function confirmCameraSelection() {
    if (!selectedDeviceId) {
        alert('Please select a camera first!');
        return;
    }
    
    cameraModal.style.display = 'none';
    initCamera(selectedDeviceId);
}

// Initialize selected camera
function initCamera(deviceId) {
    console.log('Initializing camera with device ID:', deviceId);
    updateStatus('Connecting to camera...', 'processing');
    
    // Stop existing stream if any
    if (mediaStream) {
        mediaStream.getTracks().forEach(function(track) {
            track.stop();
        });
    }
    
    let constraints = {
        video: {
            deviceId: deviceId ? { exact: deviceId } : undefined,
            width: { ideal: 1280 },
            height: { ideal: 720 }
        },
        audio: true
    };
    
    navigator.mediaDevices.getUserMedia(constraints)
        .then(function(stream) {
            video.srcObject = stream;
            mediaStream = stream;
            
            let cameraLabel = availableCameras.find(function(cam) {
                return cam.deviceId === deviceId;
            });
            
            let displayName = cameraLabel ? cameraLabel.label : 'Camera';
            cameraStatus.textContent = displayName;
            cameraStatus.style.background = 'rgba(40, 167, 69, 0.8)';
            
            console.log('Camera connected successfully:', displayName);
            updateStatus('Camera ready! Select language and click Start Interview.', 'ready');
        })
        .catch(function(err) {
            console.error("Camera connection error:", err);
            cameraStatus.textContent = 'Camera Error - Click to retry';
            cameraStatus.style.background = 'rgba(220, 53, 69, 0.8)';
            
            let errorMessage = 'Failed to connect to camera.\n\n';
            if (err.name === 'NotAllowedError') {
                errorMessage += 'Permission DENIED! Please allow camera and microphone access.';
            } else if (err.name === 'NotFoundError') {
                errorMessage += 'Camera not found! Try another camera.';
            } else if (err.name === 'NotReadableError') {
                errorMessage += 'Camera is already in use! Close other apps.';
            } else {
                errorMessage += 'Error: ' + err.message;
            }
            
            updateStatus('Failed to connect. Click camera status to retry.', 'processing');
            alert(errorMessage + '\n\nPlease try selecting a different camera.');
            
            if (availableCameras.length > 1) {
                showCameraSelector();
            }
        });
}

// Update status display
function updateStatus(message, type) {
    statusDiv.textContent = message;
    statusDiv.className = 'status ' + type;
}

// Start interview
async function startInterview() {
    if (!mediaStream) {
        alert('Please select and connect a camera first!');
        showCameraSelector();
        return;
    }
    
    console.log('Starting interview in language:', selectedLanguage);
    startBtn.disabled = true;
    stopBtn.disabled = false;
    isInterviewActive = true;
    updateStatus('Starting interview...', 'processing');
    recordingIndicator.style.display = 'block';
    
    try {
        const response = await fetch('/start_interview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ language: selectedLanguage })
        });
        
        const data = await response.json();
        
        if (data.error) {
            updateStatus('Error: ' + data.error, 'processing');
            startBtn.disabled = false;
            stopBtn.disabled = true;
            isInterviewActive = false;
            return;
        }
        
        // Hide language selector during interview
        document.getElementById('languageSelector').style.opacity = '0.5';
        document.getElementById('languageSelector').style.pointerEvents = 'none';
        
        // Speak greeting first, then ask first question
        if (data.greeting) {
            questionDiv.textContent = data.greeting;
            updateStatus('AI is greeting you...', 'speaking');
            
            // Add greeting to transcript
            const greetingHTML = '<div class="qa-pair" style="border-left-color: #667eea;">' +
                '<div class="qa-question" style="color: #667eea;">AI: ' + data.greeting + '</div>' +
                '</div>';
            transcriptDiv.innerHTML = greetingHTML;
            
            speak(data.greeting, selectedLanguage, () => {
                // After greeting, show and ask the first question
                setTimeout(() => {
                    if (isInterviewActive) {
                        askQuestion(data.question);
                    }
                }, 800);
            });
        } else {
            // No greeting, ask question directly
            askQuestion(data.question);
        }
        
    } catch (err) {
        console.error('Error:', err);
        updateStatus('Connection error. Please try again.', 'processing');
        startBtn.disabled = false;
        stopBtn.disabled = true;
        isInterviewActive = false;
    }
}

// Ask question to candidate
function askQuestion(questionText) {
    questionDiv.textContent = questionText;
    updateStatus('AI is speaking... Please listen.', 'speaking');
    
    speak(questionText, selectedLanguage, () => {
        // Automatically start listening after question is spoken
        setTimeout(() => {
            if (isInterviewActive) {
                listenForAnswer(questionText);
            }
        }, 500);
    });
}

// Listen for candidate's answer
async function listenForAnswer(currentQuestion) {
    if (isProcessing || !isInterviewActive) return;
    
    isProcessing = true;
    updateStatus('LISTENING... Please speak your answer now', 'listening');
    console.log('Listening for answer...');
    
    try {
        const response = await fetch('/listen_answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ language: selectedLanguage })
        });
        
        const data = await response.json();
        isProcessing = false;
        
        if (data.error) {
            updateStatus('Could not hear clearly. Listening again...', 'processing');
            // Auto-retry listening
            setTimeout(() => {
                if (isInterviewActive) {
                    listenForAnswer(currentQuestion);
                }
            }, 1000);
            return;
        }
        
        if (data.answer) {
            // Add Q&A to transcript
            const qaHTML = '<div class="qa-pair">' +
                '<div class="qa-question">Q: ' + currentQuestion + '</div>' +
                '<div class="qa-answer">A: ' + data.answer + '</div>' +
                '</div>';
            
            transcriptDiv.innerHTML += qaHTML;
            transcriptDiv.parentElement.scrollTop = transcriptDiv.parentElement.scrollHeight;
            
            // AI responds to the answer
            if (data.ai_response) {
                questionDiv.textContent = data.ai_response;
                updateStatus('AI is responding...', 'speaking');
                
                // Speak AI's response
                speak(data.ai_response, selectedLanguage, () => {
                    // Add AI response to transcript
                    const aiResponseHTML = '<div class="qa-pair" style="border-left-color: #28a745;">' +
                        '<div class="qa-question" style="color: #28a745;">AI: ' + data.ai_response + '</div>' +
                        '</div>';
                    transcriptDiv.innerHTML += aiResponseHTML;
                    transcriptDiv.parentElement.scrollTop = transcriptDiv.parentElement.scrollHeight;
                    
                    if (data.next_question) {
                        // Move to next question after AI responds
                        updateStatus('Processing... Next question coming', 'processing');
                        setTimeout(() => {
                            if (isInterviewActive) {
                                askQuestion(data.next_question);
                            }
                        }, 1000);
                    } else {
                        // Interview complete
                        completeInterview();
                    }
                });
            } else {
                // No AI response, move directly to next question
                if (data.next_question) {
                    setTimeout(() => {
                        if (isInterviewActive) {
                            askQuestion(data.next_question);
                        }
                    }, 1500);
                } else {
                    completeInterview();
                }
            }
        }
        
    } catch (err) {
        console.error('Error:', err);
        isProcessing = false;
        updateStatus('Connection error. Retrying...', 'processing');
        setTimeout(() => {
            if (isInterviewActive) {
                listenForAnswer(currentQuestion);
            }
        }, 2000);
    }
}

// Complete interview
async function completeInterview() {
    isInterviewActive = false;
    updateStatus('Interview completed! Generating summary...', 'processing');
    recordingIndicator.style.display = 'none';
    questionDiv.textContent = 'Thank you for completing the interview!';
    
    try {
        const response = await fetch('/stop_interview');
        const data = await response.json();
        
        if (data.summary) {
            updateStatus('Interview completed successfully!', 'ready');
            
            // Add summary to transcript
            const summaryHTML = '<div class="qa-pair" style="border-left-color: #28a745;">' +
                '<div class="qa-question" style="color: #28a745;">INTERVIEW SUMMARY:</div>' +
                '<div class="qa-answer">' + data.summary + '</div>' +
                '</div>';
            
            transcriptDiv.innerHTML += summaryHTML;
            transcriptDiv.parentElement.scrollTop = transcriptDiv.parentElement.scrollHeight;
        }
    } catch (err) {
        console.error('Error generating summary:', err);
    }
    
    startBtn.disabled = true;
    stopBtn.disabled = true;
}

// Stop interview
async function stopInterview() {
    if (!confirm('Are you sure you want to end the interview?')) {
        return;
    }
    isInterviewActive = false;
    isProcessing = false;
    completeInterview();
}

// Text-to-speech function
function speak(text, language, callback) {
    // Cancel any ongoing speech
    window.speechSynthesis.cancel();
    
    const utterance = new SpeechSynthesisUtterance(text);
    
    // Set language-specific parameters
    const langMap = {
        'english': 'en-IN',
        'hindi': 'hi-IN',
        'gujarati': 'gu-IN',
        'hinglish': 'hi-IN',
        'gujenglish': 'en-IN'
    };
    utterance.lang = langMap[language] || 'en-IN';
    
    // Adjust speech rate based on language
    if (language === 'hindi' || language === 'gujarati') {
        utterance.rate = 0.8; // Slower for Indian languages
    } else {
        utterance.rate = 0.85;
    }
    
    utterance.pitch = 1.0;
    utterance.volume = 1.0;
    
    // Try to select appropriate voice
    const voices = window.speechSynthesis.getVoices();
    const preferredVoice = voices.find(voice => 
        voice.lang.startsWith(utterance.lang.split('-')[0])
    );
    if (preferredVoice) {
        utterance.voice = preferredVoice;
        console.log('Using voice:', preferredVoice.name);
    }
    
    utterance.onend = () => {
        console.log('Finished speaking:', text.substring(0, 50) + '...');
        if (callback) callback();
    };
    
    utterance.onerror = (event) => {
        console.error('Speech error:', event);
        if (callback) callback();
    };
    
    // Small delay to ensure previous speech is cancelled
    setTimeout(() => {
        window.speechSynthesis.speak(utterance);
    }, 100);
}

// Load voices when available
window.speechSynthesis.onvoiceschanged = () => {
    const voices = window.speechSynthesis.getVoices();
    console.log('Available voices:', voices.length);
    voices.forEach(voice => {
        console.log('- ' + voice.name + ' (' + voice.lang + ')');
    });
};

// Close modal when clicking outside
window.onclick = function(event) {
    if (event.target == cameraModal) {
        cameraModal.style.display = 'none';
    }
};

// Initialize on page load
window.addEventListener('load', function() {
    console.log('Page loaded, requesting permissions and detecting cameras...');
    
    // Request permissions first, then detect all cameras
    navigator.mediaDevices.getUserMedia({ video: true, audio: true })
        .then(function(stream) {
            // Stop the temporary stream
            stream.getTracks().forEach(function(track) {
                track.stop();
            });
            // Now detect all available cameras
            detectCameras();
        })
        .catch(function(err) {
            console.error('Permission denied:', err);
            cameraStatus.textContent = 'Permission Denied';
            cameraStatus.style.background = 'rgba(220, 53, 69, 0.8)';
            updateStatus('Camera/microphone permission denied. Please allow access.', 'processing');
            alert('Please allow camera and microphone access to use this application.\n\nClick the camera icon in the address bar to manage permissions.');
        });
});

