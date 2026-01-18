import os
import time
import speech_recognition as sr
import google.generativeai as genai
from flask import Flask, render_template_string, jsonify, request
import threading
import webbrowser
import dotenv

# Configure Gemini API
dotenv.load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash-exp')

app = Flask(__name__)

# Language configuration
LANGUAGE_CONFIG = {
    'english': {
        'name': 'English',
        'speech_code': 'en-IN',
        'voice_lang': 'en-IN',
        'prompt_instruction': 'Ask interview questions in English.'
    },
    'hindi': {
        'name': 'Hindi (हिंदी)',
        'speech_code': 'hi-IN',
        'voice_lang': 'hi-IN',
        'prompt_instruction': 'Ask interview questions in Hindi language only. Use Devanagari script.'
    },
    'gujarati': {
        'name': 'Gujarati (ગુજરાતી)',
        'speech_code': 'gu-IN',
        'voice_lang': 'gu-IN',
        'prompt_instruction': 'Ask interview questions in Gujarati language only. Use Gujarati script.'
    },
    'hinglish': {
        'name': 'Hindi + English (Hinglish)',
        'speech_code': 'hi-IN',
        'voice_lang': 'hi-IN',
        'prompt_instruction': 'Ask interview questions in a natural mix of Hindi and English (Hinglish). Use both languages fluidly.'
    },
    'gujenglish': {
        'name': 'Gujarati + English',
        'speech_code': 'gu-IN',
        'voice_lang': 'en-IN',
        'prompt_instruction': 'Ask interview questions in a natural mix of Gujarati and English. Use both languages fluidly.'
    }
}

# Interview state
interview_data = {
    'questions': [],
    'answers': [],
    'current_question': '',
    'current_index': 0,
    'interview_active': False,
    'selected_language': 'english',
    'total_questions': 5
}

def generate_interview_question(question_number, language_key):
    """Generate interview question using Gemini based on language preference"""
    lang_config = LANGUAGE_CONFIG[language_key]
    
    prompt = f"""You are conducting a professional job interview. {lang_config['prompt_instruction']}

Generate interview question #{question_number} for a candidate. The question should be:
- Professional and respectful
- Clear and conversational
- Appropriate for a general job interview

Question types to rotate through:
1. Background and experience
2. Strengths and skills
3. Problem-solving and challenges
4. Career goals and aspirations
5. Motivation and interest

Return ONLY the question text, nothing else. Make it sound natural and conversational."""

    try:
        response = model.generate_content(prompt)
        question = response.text.strip()
        print(f"Generated Question {question_number}: {question}")
        return question
    except Exception as e:
        print(f"Error generating question: {e}")
        # Fallback questions in English
        fallback = [
            "Tell me about yourself and your background.",
            "What are your greatest strengths?",
            "Describe a challenging project you have worked on.",
            "Where do you see yourself in 5 years?",
            "Why are you interested in this position?"
        ]
        return fallback[min(question_number - 1, 4)]

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>AI Video Interview - Multilingual</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 10px;
            font-size: 32px;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }
        
        /* Language Selection */
        .language-selector {
            background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 25px;
            border: 2px solid #667eea;
        }
        .language-selector h3 {
            margin-bottom: 15px;
            color: #333;
            font-size: 18px;
        }
        .language-options {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px;
        }
        .language-option {
            background: white;
            padding: 15px;
            border-radius: 10px;
            cursor: pointer;
            border: 2px solid #dee2e6;
            transition: all 0.3s;
            text-align: center;
            font-weight: 500;
        }
        .language-option:hover {
            border-color: #667eea;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }
        .language-option.selected {
            border-color: #28a745;
            background: linear-gradient(135deg, #28a74515 0%, #20c99715 100%);
            font-weight: 600;
        }
        
        #video-container {
            position: relative;
            width: 100%;
            max-width: 640px;
            margin: 0 auto 30px;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            background: #000;
        }
        #video {
            width: 100%;
            height: 480px;
            display: block;
            object-fit: cover;
        }
        .recording-indicator {
            position: absolute;
            top: 15px;
            right: 15px;
            background: #ff0000;
            color: white;
            padding: 8px 15px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: bold;
            display: none;
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }
        .camera-status {
            position: absolute;
            top: 15px;
            left: 15px;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 8px 15px;
            border-radius: 20px;
            font-size: 12px;
        }
        .status {
            text-align: center;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 25px;
            font-weight: 600;
            font-size: 16px;
            transition: all 0.3s;
        }
        .status.ready { background: #e3f2fd; color: #1976d2; }
        .status.listening { 
            background: #d4edda; 
            color: #155724;
            animation: listening-pulse 2s infinite;
        }
        @keyframes listening-pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.02); }
        }
        .status.speaking { background: #fff3cd; color: #856404; }
        .status.processing { background: #f8d7da; color: #721c24; }
        
        .question-box {
            background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 25px;
            border-left: 5px solid #667eea;
            min-height: 100px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        .question-label {
            font-size: 14px;
            color: #666;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .question-text {
            font-size: 22px;
            color: #333;
            font-weight: 500;
            line-height: 1.6;
        }
        .controls {
            text-align: center;
            margin: 30px 0;
            display: flex;
            gap: 15px;
            justify-content: center;
            flex-wrap: wrap;
        }
        button {
            padding: 15px 35px;
            font-size: 16px;
            font-weight: 600;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .start-btn {
            background: linear-gradient(135deg, #28a745, #20c997);
            color: white;
            font-size: 18px;
            padding: 18px 45px;
        }
        .start-btn:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(40,167,69,0.4);
        }
        .stop-btn {
            background: linear-gradient(135deg, #dc3545, #c82333);
            color: white;
        }
        .stop-btn:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(220,53,69,0.4);
        }
        .transcript {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-top: 30px;
            max-height: 400px;
            overflow-y: auto;
            border: 2px solid #dee2e6;
        }
        .transcript strong {
            color: #667eea;
            font-size: 18px;
        }
        #transcript-content {
            margin-top: 15px;
        }
        .qa-pair {
            margin-bottom: 20px;
            padding: 15px;
            background: white;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        .qa-question {
            color: #667eea;
            font-weight: bold;
            margin-bottom: 8px;
            font-size: 15px;
        }
        .qa-answer {
            color: #333;
            padding-left: 15px;
            line-height: 1.6;
            font-size: 14px;
        }
        .hidden {
            display: none;
        }
        
        /* Camera Selection Modal */
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.8);
        }
        .modal-content {
            background-color: #fefefe;
            margin: 8% auto;
            padding: 30px;
            border-radius: 15px;
            width: 90%;
            max-width: 500px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.5);
        }
        .modal-header {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 20px;
            color: #333;
            text-align: center;
        }
        .camera-option-item {
            background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
            padding: 15px;
            margin: 10px 0;
            border-radius: 10px;
            cursor: pointer;
            border: 2px solid transparent;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .camera-option-item:hover {
            border-color: #667eea;
            transform: translateX(5px);
        }
        .camera-option-item.selected {
            border-color: #28a745;
            background: linear-gradient(135deg, #28a74515 0%, #20c99715 100%);
        }
        .camera-icon {
            font-size: 24px;
        }
        .camera-info {
            flex: 1;
        }
        .camera-name {
            font-weight: 600;
            color: #333;
            margin-bottom: 3px;
        }
        .camera-id {
            font-size: 12px;
            color: #666;
        }
        .select-camera-btn {
            width: 100%;
            padding: 12px;
            margin-top: 20px;
            background: linear-gradient(135deg, #28a745, #20c997);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        .select-camera-btn:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(40,167,69,0.4);
        }
        .select-camera-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>AI Video Interview System</h1>
        <div class="subtitle">Multilingual | Smooth Conversation Flow | Powered by Gemini</div>
        
        <!-- Language Selection -->
        <div class="language-selector" id="languageSelector">
            <h3>Select Your Interview Language:</h3>
            <div class="language-options">
                <div class="language-option selected" data-lang="english">English</div>
                <div class="language-option" data-lang="hindi">Hindi (हिंदी)</div>
                <div class="language-option" data-lang="gujarati">Gujarati (ગુજરાતી)</div>
                <div class="language-option" data-lang="hinglish">Hindi + English</div>
                <div class="language-option" data-lang="gujenglish">Gujarati + English</div>
            </div>
        </div>
        
        <div id="video-container">
            <video id="video" autoplay playsinline muted></video>
            <div class="camera-status" id="cameraStatus" onclick="showCameraSelector()" style="cursor: pointer;">Select Camera</div>
            <div class="recording-indicator" id="recordingIndicator">REC</div>
        </div>
        
        <div id="status" class="status ready">Select your language and click Start Interview</div>
        
        <div class="question-box">
            <div class="question-label">AI Interviewer:</div>
            <div class="question-text" id="question">Welcome! Select your preferred language and click Start Interview to begin.</div>
        </div>
        
        <div class="controls">
            <button class="start-btn" onclick="startInterview()" id="startBtn">Start Interview</button>
            <button class="stop-btn" onclick="stopInterview()" id="stopBtn" disabled>End Interview</button>
        </div>
        
        <div class="transcript">
            <strong>Interview Transcript</strong>
            <div id="transcript-content">Your conversation will appear here...</div>
        </div>
    </div>

    <!-- Camera Selection Modal -->
    <div id="cameraModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">Select Your Camera</div>
            <div id="cameraList"></div>
            <button class="select-camera-btn" id="confirmCameraBtn" onclick="confirmCameraSelection()">Use Selected Camera</button>
        </div>
    </div>

    <script>
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
                    
                    let errorMessage = 'Failed to connect to camera.\\n\\n';
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
                    alert(errorMessage + '\\n\\nPlease try selecting a different camera.');
                    
                    if (availableCameras.length > 1) {
                        showCameraSelector();
                    }
                });
        }

        function updateStatus(message, type) {
            statusDiv.textContent = message;
            statusDiv.className = 'status ' + type;
        }

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
                
                askQuestion(data.question);
                
            } catch (err) {
                console.error('Error:', err);
                updateStatus('Connection error. Please try again.', 'processing');
                startBtn.disabled = false;
                stopBtn.disabled = true;
                isInterviewActive = false;
            }
        }

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
                    // Add to transcript
                    const qaHTML = '<div class="qa-pair">' +
                        '<div class="qa-question">Q: ' + currentQuestion + '</div>' +
                        '<div class="qa-answer">A: ' + data.answer + '</div>' +
                        '</div>';
                    
                    transcriptDiv.innerHTML += qaHTML;
                    transcriptDiv.parentElement.scrollTop = transcriptDiv.parentElement.scrollHeight;
                    
                    if (data.next_question) {
                        // Automatically move to next question
                        updateStatus('Processing... Next question coming', 'processing');
                        setTimeout(() => {
                            if (isInterviewActive) {
                                askQuestion(data.next_question);
                            }
                        }, 1500);
                    } else {
                        // Interview complete
                        completeInterview();
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

        async function stopInterview() {
            if (!confirm('Are you sure you want to end the interview?')) {
                return;
            }
            isInterviewActive = false;
            isProcessing = false;
            completeInterview();
        }

        function speak(text, language, callback) {
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 0.85;
            utterance.pitch = 1.0;
            utterance.volume = 1.0;
            
            // Set language for speech
            const langMap = {
                'english': 'en-IN',
                'hindi': 'hi-IN',
                'gujarati': 'gu-IN',
                'hinglish': 'hi-IN',
                'gujenglish': 'en-IN'
            };
            utterance.lang = langMap[language] || 'en-IN';
            
            utterance.onend = () => {
                console.log('Finished speaking');
                if (callback) callback();
            };
            
            utterance.onerror = (event) => {
                console.error('Speech error:', event);
                if (callback) callback();
            };
            
            window.speechSynthesis.speak(utterance);
        }

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
                    alert('Please allow camera and microphone access to use this application.\\n\\nClick the camera icon in the address bar to manage permissions.');
                });
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/start_interview', methods=['POST'])
def start_interview():
    try:
        data = request.get_json()
        language = data.get('language', 'english')
        
        interview_data['interview_active'] = True
        interview_data['current_index'] = 0
        interview_data['questions'] = []
        interview_data['answers'] = []
        interview_data['selected_language'] = language
        
        # Generate first question using Gemini
        first_question = generate_interview_question(1, language)
        interview_data['current_question'] = first_question
        
        print(f"\n{'='*50}")
        print(f"INTERVIEW STARTED - Language: {LANGUAGE_CONFIG[language]['name']}")
        print(f"{'='*50}")
        print(f"Question 1: {first_question}")
        
        return jsonify({
            'status': 'success',
            'question': first_question
        })
    except Exception as e:
        print(f"Error starting interview: {e}")
        return jsonify({'error': str(e)})

@app.route('/listen_answer', methods=['POST'])
def listen_answer():
    recognizer = sr.Recognizer()
    answer_text = ""
    
    try:
        data = request.get_json()
        language = data.get('language', 'english')
        lang_config = LANGUAGE_CONFIG[language]
        
        print(f"\nListening for answer in {lang_config['name']}...")
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            print("Speak now...")
            audio = recognizer.listen(source, timeout=15, phrase_time_limit=60)
            
        print("Processing speech...")
        # Use appropriate language code for speech recognition
        answer_text = recognizer.recognize_google(audio, language=lang_config['speech_code'])
        print(f"Transcribed answer: {answer_text}")
        
        interview_data['answers'].append(answer_text)
        current_question = interview_data['current_question']
        interview_data['questions'].append(current_question)
        
        # Move to next question
        interview_data['current_index'] += 1
        
        if interview_data['current_index'] < interview_data['total_questions']:
            # Generate next question using Gemini
            next_question = generate_interview_question(
                interview_data['current_index'] + 1,
                language
            )
            interview_data['current_question'] = next_question
            
            print(f"\nQuestion {interview_data['current_index'] + 1}: {next_question}")
            
            return jsonify({
                'status': 'success',
                'answer': answer_text,
                'question': current_question,
                'next_question': next_question
            })
        else:
            # Interview complete
            print("\nAll questions completed!")
            interview_data['interview_active'] = False
            return jsonify({
                'status': 'complete',
                'answer': answer_text,
                'question': current_question,
                'next_question': None
            })
            
    except sr.WaitTimeoutError:
        print("Timeout - no speech detected")
        return jsonify({'error': 'No speech detected'})
    except sr.UnknownValueError:
        print("Could not understand audio")
        return jsonify({'error': 'Could not understand'})
    except sr.RequestError as e:
        print(f"Speech recognition error: {e}")
        return jsonify({'error': 'Recognition service error'})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)})

@app.route('/stop_interview')
def stop_interview():
    interview_data['interview_active'] = False
    summary = None
    
    try:
        if len(interview_data['answers']) > 0:
            # Generate summary using Gemini
            qa_pairs = "\n\n".join([
                f"Q{i+1}: {q}\nA{i+1}: {a}" 
                for i, (q, a) in enumerate(zip(interview_data['questions'], interview_data['answers']))
            ])
            
            language = interview_data['selected_language']
            lang_config = LANGUAGE_CONFIG[language]
            
            summary_prompt = f"""You are an expert interviewer. Based on this interview, provide a brief professional assessment of the candidate.

Interview Language: {lang_config['name']}
Interview Transcript:
{qa_pairs}

Provide a concise 4-5 sentence assessment in {lang_config['name']} covering:
1. Communication skills
2. Key strengths demonstrated
3. Overall impression
4. Recommendation

Be professional and constructive. {lang_config['prompt_instruction']}"""
            
            print("\nGenerating interview summary...")
            response = model.generate_content(summary_prompt)
            summary = response.text
            
            print(f"\n{'='*50}")
            print("INTERVIEW SUMMARY")
            print(f"{'='*50}")
            print(summary)
            print(f"{'='*50}\n")
        
    except Exception as e:
        print(f"Error generating summary: {e}")
        summary = "Could not generate summary."
    
    return jsonify({
        'status': 'Interview ended',
        'summary': summary
    })

def open_browser():
    time.sleep(2)
    webbrowser.open('http://127.0.0.1:5000')

if __name__ == '__main__':
    print(f"\n{'='*70}")
    print("AI MULTILINGUAL VIDEO INTERVIEW - POWERED BY GEMINI")
    print(f"{'='*70}")
    print("Languages: English | Hindi | Gujarati | Hinglish | Gujarati+English")
    print("Features: Smooth Auto-Conversation | No Manual Buttons | AI-Generated Questions")
    print(f"{'='*70}")
    print("Starting Flask server...")
    print("Opening browser automatically...")
    print("Please ALLOW camera and microphone access!")
    print(f"{'='*70}\n")
    
    threading.Thread(target=open_browser, daemon=True).start()
    app.run(debug=False, port=5000, threaded=True)
