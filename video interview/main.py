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
model = genai.GenerativeModel('gemini-2.5-flash')

app = Flask(__name__)

# Interview state
interview_data = {
    'questions': [],
    'answers': [],
    'current_question': '',
    'current_index': 0,
    'is_listening': False,
    'interview_active': False
}

# Interview questions
INTERVIEW_QUESTIONS = [
    "Tell me about yourself and your background.",
    "What are your greatest strengths?",
    "Describe a challenging project you've worked on.",
    "Where do you see yourself in 5 years?",
    "Why are you interested in this position?"
]

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>AI Video Interview</title>
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
            margin-bottom: 30px;
            font-size: 32px;
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
            background-color: rgba(0,0,0,0.7);
        }
        .modal-content {
            background-color: #fefefe;
            margin: 10% auto;
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
        .camera-option {
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
        .camera-option:hover {
            border-color: #667eea;
            transform: translateX(5px);
        }
        .camera-option.selected {
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
        .select-camera-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(40,167,69,0.4);
        }
        .select-camera-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
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
            cursor: pointer;
        }
        .camera-status:hover {
            background: rgba(0,0,0,0.9);
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
        .status.listening { background: #d4edda; color: #155724; }
        .status.speaking { background: #fff3cd; color: #856404; }
        .status.processing { background: #f8d7da; color: #721c24; }
        
        .question-box {
            background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 25px;
            border-left: 5px solid #667eea;
            min-height: 80px;
        }
        .question-label {
            font-size: 14px;
            color: #666;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .question-text {
            font-size: 20px;
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
        }
        .start-btn:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(40,167,69,0.4);
        }
        .answer-btn {
            background: linear-gradient(135deg, #007bff, #0056b3);
            color: white;
        }
        .answer-btn:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0,123,255,0.4);
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
            max-height: 300px;
            overflow-y: auto;
            border: 2px solid #dee2e6;
        }
        .transcript strong {
            color: #667eea;
            font-size: 18px;
        }
        #transcript-content {
            margin-top: 15px;
            white-space: pre-wrap;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            line-height: 1.8;
        }
        .qa-pair {
            margin-bottom: 20px;
            padding-bottom: 20px;
            border-bottom: 1px solid #dee2e6;
        }
        .qa-question {
            color: #667eea;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .qa-answer {
            color: #333;
            padding-left: 15px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎥 AI Video Interview System</h1>
        
        <div id="video-container">
            <video id="video" autoplay playsinline muted></video>
            <div class="camera-status" id="cameraStatus" onclick="showCameraSelector()">🎥 Select Camera</div>
            <div class="recording-indicator" id="recordingIndicator">● REC</div>
        </div>
        
        <div id="status" class="status ready">Select your camera to begin</div>
        
        <div class="question-box">
            <div class="question-label">Current Question:</div>
            <div class="question-text" id="question">Click "Start Interview" to begin the session</div>
        </div>
        
        <div class="controls">
            <button class="start-btn" id="startBtn">▶ Start Interview</button>
            <button class="answer-btn" id="answerBtn" disabled>🎤 Answer Question</button>
            <button class="stop-btn" id="stopBtn">⏹ End Interview</button>
        </div>
        
        <div class="transcript">
            <strong>📝 Interview Transcript</strong>
            <div id="transcript-content">No transcript yet. Start the interview to begin.</div>
        </div>
    </div>

    <!-- Camera Selection Modal -->
    <div id="cameraModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">📹 Select Your Camera</div>
            <div id="cameraList"></div>
            <button class="select-camera-btn" id="confirmCameraBtn" onclick="confirmCameraSelection()">Use Selected Camera</button>
        </div>
    </div>

    <script>
        var video = document.getElementById('video');
        var statusDiv = document.getElementById('status');
        var questionDiv = document.getElementById('question');
        var transcriptDiv = document.getElementById('transcript-content');
        var answerBtn = document.getElementById('answerBtn');
        var startBtn = document.getElementById('startBtn');
        var stopBtn = document.getElementById('stopBtn');
        var recordingIndicator = document.getElementById('recordingIndicator');
        var cameraStatus = document.getElementById('cameraStatus');
        var cameraModal = document.getElementById('cameraModal');
        var cameraList = document.getElementById('cameraList');
        var confirmCameraBtn = document.getElementById('confirmCameraBtn');
        
        var mediaStream = null;
        var availableCameras = [];
        var selectedDeviceId = null;

        function updateStatus(message, type) {
            statusDiv.textContent = message;
            statusDiv.className = 'status ' + type;
        }

        function detectCameras() {
            console.log('Detecting available cameras...');
            
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
                        alert('No cameras found. Please connect a USB camera or webcam and refresh the page.');
                    } else {
                        showCameraSelector();
                    }
                })
                .catch(function(err) {
                    console.error('Error detecting cameras:', err);
                    updateStatus('Error detecting cameras. Check permissions.', 'processing');
                });
        }

        function showCameraSelector() {
            if (availableCameras.length === 0) {
                detectCameras();
                return;
            }
            
            cameraList.innerHTML = '';
            
            availableCameras.forEach(function(camera, index) {
                var option = document.createElement('div');
                option.className = 'camera-option';
                option.setAttribute('data-device-id', camera.deviceId);
                
                var label = camera.label || 'Camera ' + (index + 1);
                
                // Identify camera types
                var icon = '📹';
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
                    document.querySelectorAll('.camera-option').forEach(function(opt) {
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

        function confirmCameraSelection() {
            if (!selectedDeviceId) {
                alert('Please select a camera first!');
                return;
            }
            
            cameraModal.style.display = 'none';
            initCamera(selectedDeviceId);
        }

        function initCamera(deviceId) {
            console.log('Initializing camera with device ID:', deviceId);
            updateStatus('Connecting to camera...', 'processing');
            
            // Stop existing stream if any
            if (mediaStream) {
                mediaStream.getTracks().forEach(function(track) {
                    track.stop();
                });
            }
            
            var constraints = {
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
                    
                    var cameraLabel = availableCameras.find(function(cam) {
                        return cam.deviceId === deviceId;
                    });
                    
                    var displayName = cameraLabel ? cameraLabel.label : 'Camera';
                    cameraStatus.textContent = '✓ ' + displayName;
                    cameraStatus.style.background = 'rgba(40, 167, 69, 0.8)';
                    
                    console.log('Camera connected successfully:', displayName);
                    updateStatus('Camera ready! Click "Start Interview" to begin.', 'ready');
                })
                .catch(function(err) {
                    console.error("Camera connection error:", err);
                    cameraStatus.textContent = '✗ Camera Error';
                    cameraStatus.style.background = 'rgba(220, 53, 69, 0.8)';
                    updateStatus('Failed to connect to camera. Try another camera.', 'processing');
                    alert('Camera Error: ' + err.message + '\\n\\nPlease try selecting a different camera.');
                    showCameraSelector();
                });
        }

        function startInterview() {
            if (!mediaStream) {
                alert('Please select and connect a camera first!');
                showCameraSelector();
                return;
            }
            
            console.log('Starting interview...');
            startBtn.disabled = true;
            updateStatus('Starting interview...', 'processing');
            
            fetch('/start_interview')
                .then(function(response) { return response.json(); })
                .then(function(data) {
                    if (data.error) {
                        updateStatus('Error: ' + data.error, 'processing');
                        startBtn.disabled = false;
                        return;
                    }
                    questionDiv.textContent = data.question;
                    updateStatus('🔊 Listen to the question...', 'speaking');
                    recordingIndicator.style.display = 'block';
                    
                    speak(data.question, function() {
                        answerBtn.disabled = false;
                        updateStatus('Ready! Click "Answer Question" to respond.', 'ready');
                    });
                })
                .catch(function(err) {
                    console.error('Error starting interview:', err);
                    updateStatus('Connection error. Please try again.', 'processing');
                    startBtn.disabled = false;
                });
        }

        function answerQuestion() {
            answerBtn.disabled = true;
            updateStatus('🎤 LISTENING... Please speak your answer now.', 'listening');
            console.log('Listening for answer...');
            
            fetch('/listen_answer')
                .then(function(response) { return response.json(); })
                .then(function(data) {
                    console.log('Response received:', data);
                    
                    if (data.error) {
                        updateStatus('Error: ' + data.error + ' - Try again.', 'processing');
                        answerBtn.disabled = false;
                        return;
                    }
                    
                    if (data.answer) {
                        var qaHTML = '<div class="qa-pair">' +
                            '<div class="qa-question">Q: ' + data.question + '</div>' +
                            '<div class="qa-answer">A: ' + data.answer + '</div>' +
                            '</div>';
                        
                        transcriptDiv.innerHTML += qaHTML;
                        transcriptDiv.parentElement.scrollTop = transcriptDiv.parentElement.scrollHeight;
                        
                        if (data.next_question) {
                            questionDiv.textContent = data.next_question;
                            updateStatus('🔊 Next question...', 'speaking');
                            
                            speak(data.next_question, function() {
                                answerBtn.disabled = false;
                                updateStatus('Ready for your next answer!', 'ready');
                            });
                        } else {
                            updateStatus('✅ Interview completed! Thank you.', 'ready');
                            recordingIndicator.style.display = 'none';
                            answerBtn.disabled = true;
                            startBtn.disabled = true;
                            questionDiv.textContent = 'Interview completed. Check transcript below.';
                        }
                    } else {
                        updateStatus('Could not hear clearly. Try again.', 'processing');
                        answerBtn.disabled = false;
                    }
                })
                .catch(function(err) {
                    console.error('Error during answer:', err);
                    updateStatus('Connection error. Try again.', 'processing');
                    answerBtn.disabled = false;
                });
        }

        function stopInterview() {
            updateStatus('Ending interview...', 'processing');
            
            fetch('/stop_interview')
                .then(function(response) { return response.json(); })
                .then(function(data) {
                    updateStatus('Interview ended.', 'ready');
                    recordingIndicator.style.display = 'none';
                    answerBtn.disabled = true;
                    startBtn.disabled = true;
                    questionDiv.textContent = 'Interview session ended.';
                    
                    if (data.summary) {
                        alert('Interview Summary:\\n\\n' + data.summary);
                    }
                });
        }

        function speak(text, callback) {
            var utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 0.85;
            utterance.pitch = 1.0;
            utterance.volume = 1.0;
            
            utterance.onend = function() {
                console.log('Finished speaking');
                if (callback) callback();
            };
            
            utterance.onerror = function(event) {
                console.error('Speech error:', event);
                if (callback) callback();
            };
            
            window.speechSynthesis.speak(utterance);
        }

        // Add event listeners
        startBtn.addEventListener('click', startInterview);
        answerBtn.addEventListener('click', answerQuestion);
        stopBtn.addEventListener('click', stopInterview);

        // Close modal when clicking outside
        window.onclick = function(event) {
            if (event.target == cameraModal) {
                cameraModal.style.display = 'none';
            }
        };

        // Initialize - detect cameras when page loads
        window.addEventListener('load', function() {
            console.log('Page loaded, detecting cameras...');
            
            // Request permissions first
            navigator.mediaDevices.getUserMedia({ video: true, audio: true })
                .then(function(stream) {
                    // Stop the temporary stream
                    stream.getTracks().forEach(function(track) {
                        track.stop();
                    });
                    // Now detect all cameras
                    detectCameras();
                })
                .catch(function(err) {
                    console.error('Permission denied:', err);
                    updateStatus('Camera/microphone permission denied. Please allow access.', 'processing');
                    alert('Please allow camera and microphone access to use this application.');
                });
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/start_interview')
def start_interview():
    try:
        interview_data['interview_active'] = True
        interview_data['current_index'] = 0
        interview_data['current_question'] = INTERVIEW_QUESTIONS[0]
        interview_data['questions'] = []
        interview_data['answers'] = []
        
        print(f"\n{'='*50}")
        print("INTERVIEW STARTED")
        print(f"{'='*50}")
        print(f"Question 1: {interview_data['current_question']}")
        
        return jsonify({
            'status': 'success',
            'question': interview_data['current_question']
        })
    except Exception as e:
        print(f"Error starting interview: {e}")
        return jsonify({'error': str(e)})

@app.route('/listen_answer')
def listen_answer():
    recognizer = sr.Recognizer()
    answer_text = ""
    
    try:
        print("\nListening for answer...")
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            print("Speak now...")
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=45)
            
        print("Processing speech...")
        answer_text = recognizer.recognize_google(audio)
        print(f"Transcribed answer: {answer_text}")
        
        interview_data['answers'].append(answer_text)
        current_question = interview_data['current_question']
        interview_data['questions'].append(current_question)
        
        # Move to next question
        interview_data['current_index'] += 1
        
        if interview_data['current_index'] < len(INTERVIEW_QUESTIONS):
            next_question = INTERVIEW_QUESTIONS[interview_data['current_index']]
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
        return jsonify({'error': 'No speech detected. Please try again.'})
    except sr.UnknownValueError:
        print("Could not understand audio")
        return jsonify({'error': 'Could not understand. Please speak clearly.'})
    except sr.RequestError as e:
        print(f"Speech recognition service error: {e}")
        return jsonify({'error': 'Speech recognition service unavailable.'})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': f'An error occurred: {str(e)}'})

@app.route('/stop_interview')
def stop_interview():
    interview_data['interview_active'] = False
    summary = None
    
    try:
        if len(interview_data['answers']) > 0:
            # Generate interview summary using Gemini
            qa_pairs = "\n\n".join([
                f"Q{i+1}: {q}\nA{i+1}: {a}" 
                for i, (q, a) in enumerate(zip(interview_data['questions'], interview_data['answers']))
            ])
            
            summary_prompt = f"""You are an expert interviewer. Based on this interview, provide a brief professional assessment of the candidate.

Interview Transcript:
{qa_pairs}

Provide a concise 3-4 sentence assessment covering:
1. Communication skills
2. Key strengths demonstrated
3. Overall impression

Keep it professional and constructive."""
            
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
        summary = "Could not generate summary due to an error."
    
    return jsonify({
        'status': 'Interview ended',
        'summary': summary
    })

@app.route('/get_status')
def get_status():
    return jsonify({
        'active': interview_data['interview_active'],
        'current_index': interview_data['current_index'],
        'total_questions': len(INTERVIEW_QUESTIONS)
    })

def open_browser():
    time.sleep(2)
    webbrowser.open('http://127.0.0.1:5000')

if __name__ == '__main__':
    print(f"\n{'='*60}")
    print("AI VIDEO INTERVIEW SYSTEM - POWERED BY GEMINI 2.0 FLASH")
    print(f"{'='*60}")
    print("🚀 Starting Flask server...")
    print("🌐 Opening browser automatically...")
    print("📹 You will be able to SELECT your camera (USB/Built-in)")
    print("🎤 Please ALLOW camera and microphone access when prompted!")
    print(f"{'='*60}\n")
    
    threading.Thread(target=open_browser, daemon=True).start()
    app.run(debug=False, port=5000, threaded=True)