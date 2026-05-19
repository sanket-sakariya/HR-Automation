"""
Aptitude Test Flask Service
This service generates and serves HTML aptitude test forms.
It has no database access and uses the main app's API endpoint.
"""
import os
import logging
from pathlib import Path
from flask import Flask, render_template_string, request, send_from_directory, jsonify

# Configuration
SERVICE_HOST = 'localhost'
SERVICE_PORT = 8890
DEBUG_MODE = True
TESTS_DIRECTORY_NAME = 'tests'
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Configure logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL), format=LOG_FORMAT)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Get the directory where this script is located
BASE_DIR = Path(__file__).parent
TESTS_DIR = BASE_DIR / TESTS_DIRECTORY_NAME

# Create tests directory if it doesn't exist
TESTS_DIR.mkdir(exist_ok=True)

# HTML Template for the aptitude test
APTITUDE_TEST_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ test_title }} - Aptitude Test</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            background: #f5f5f5;
            min-height: 100vh;
            padding: 40px 0;
        }
        .test-container {
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            padding: 0;
            max-width: 1000px;
            margin: 0 auto;
            overflow: hidden;
        }
        .test-header {
            background: #1a1a1a;
            color: white;
            padding: 30px;
            text-align: center;
        }
        .test-info {
            background: white;
            padding: 20px;
            border-bottom: 3px solid #000;
        }
        .test-info-item {
            display: inline-block;
            margin: 0 15px;
        }
        .test-content {
            padding: 30px;
        }
        .question-card {
            background: white;
            border-left: 4px solid #000;
            padding: 20px;
            margin-bottom: 25px;
            border-radius: 8px;
            border: 1px solid #000;
        }
        .question-number {
            background: #000;
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-weight: 600;
            display: inline-block;
            margin-bottom: 10px;
        }
        .question-text {
            font-size: 1.1rem;
            font-weight: 500;
            color: #000;
            margin: 15px 0;
        }
        .difficulty-badge {
            font-size: 0.85rem;
            padding: 4px 10px;
            border-radius: 12px;
            margin-left: 10px;
        }
        .difficulty-simple {
            background: #000;
            color: white;
        }
        .difficulty-medium {
            background: #000;
            color: white;
        }
        .difficulty-hard {
            background: #000;
            color: white;
        }
        .category-badge {
            background: #000;
            color: white;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.85rem;
            margin-left: 5px;
        }
        .option-label {
            cursor: pointer;
            padding: 12px;
            border: 2px solid #000;
            border-radius: 8px;
            margin: 8px 0;
            transition: all 0.2s;
        }
        .option-label:hover {
            background: #f0f0f0;
            border-color: #000;
        }
        .option-label input[type="radio"]:checked + .option-text {
            font-weight: 600;
        }
        .option-label input[type="radio"]:checked {
            transform: scale(1.1);
        }
        .timer {
            position: fixed;
            top: 20px;
            right: 20px;
            background: white;
            padding: 15px 25px;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            font-size: 1.2rem;
            font-weight: 600;
            color: #000;
            border: 2px solid #000;
        }
        .timer.warning {
            background: white;
            color: #000;
            border-color: #000;
        }
        .timer.danger {
            background: #000;
            color: white;
            border-color: #000;
            animation: pulse 1s infinite;
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }
        .btn-submit {
            background: #000;
            border: none;
            padding: 12px 40px;
            font-weight: 600;
            transition: transform 0.2s;
        }
        .btn-submit:hover {
            background: #333;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
        }
        .progress-indicator {
            padding: 15px 30px;
            background: white;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .progress-bar {
            background: #000;
        }
        .success-message, .error-message {
            display: none;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .success-message {
            background: #f0f0f0;
            border: 2px solid #333;
            color: #1a1a1a;
        }
        .error-message {
            background: #fff;
            border: 2px solid #1a1a1a;
            color: #1a1a1a;
        }
        /* Fullscreen mode styles */
        body.fullscreen-active {
            overflow-y: auto !important;
            height: 100vh !important;
        }
        .timer {
            position: fixed !important;
            top: 50px !important;
            right: 10px !important;
            z-index: 10000 !important;
        }
        body:not(.fullscreen-active) .timer {
            top: 10px !important;
        }
        body.fullscreen-active .container {
            margin: 0 !important;
            padding: 20px !important;
            max-width: none !important;
            min-height: 100vh !important;
        }
        body.fullscreen-active .test-container {
            margin: 0 !important;
            border-radius: 0 !important;
        }
        .fullscreen-warning {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            background: #000;
            color: white;
            text-align: center;
            padding: 10px;
            z-index: 10001;
            font-weight: bold;
        }
        body.fullscreen-active .fullscreen-warning {
            display: block !important;
        }
        #fullscreenEntry button:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.4) !important;
        }
    </style>
</head>
<body>
    <script>
        // Session guard: allow access only with a valid session token stored in sessionStorage.
        // No token is kept in the URL; token must exist in sessionStorage for this origin/tab.
        (function() {
            const sessionKey = `test_session_{{ job_requirement_id }}_{{ aptitude_test_id }}`;
            const storedToken = sessionStorage.getItem(sessionKey);

            if (!storedToken) {
                const loginUrl = `http://localhost:8890/tests/login_{{ job_requirement_id }}_{{ aptitude_test_id }}.html`;
                window.location.replace(loginUrl);
                return;
            }
        })();
    </script>

    <!-- Fullscreen Entry Screen -->
    <div id="fullscreenEntry" style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: #000; z-index: 99999; display: flex; align-items: center; justify-content: center;">
        <div style="text-align: center; color: white;">
            <h1 style="font-size: 3rem; margin-bottom: 30px;">🧠 Aptitude Test</h1>
            <p style="font-size: 1.5rem; margin-bottom: 40px;">{{ test_title }}</p>
            <button onclick="startTest()" style="background: white; color: #000; border: none; padding: 20px 60px; font-size: 1.5rem; font-weight: 600; border-radius: 50px; cursor: pointer; box-shadow: 0 10px 30px rgba(0,0,0,0.3); transition: transform 0.2s;">
                🚀 Start Test in Fullscreen
            </button>
            <p style="margin-top: 30px; font-size: 1rem; opacity: 0.9;">⚠️ The test will open in fullscreen mode. Do not exit fullscreen during the test.</p>
        </div>
    </div>

    <!-- Fullscreen Warning -->
    <div class="fullscreen-warning" id="fullscreenWarning">
        ⚠️ Test is in Fullscreen Mode - Do not exit fullscreen
    </div>

    <!-- Timer -->
    <div id="timer" class="timer">
        ⏱️ <span id="timeRemaining">{{ total_time_minutes }}:00</span>
    </div>

    <div class="container">
        <div class="test-container">
            <!-- Test Header -->
            <div class="test-header">
                <h1 class="mb-2">🧠 {{ test_title }}</h1>
                <p class="mb-0">Aptitude Assessment</p>
            </div>

            <!-- Test Info -->
            <div class="test-info text-center">
                <div class="test-info-item">
                    <strong>📋 Total Questions:</strong> {{ total_questions }}
                    </div>
                <div class="test-info-item">
                    <strong>⏱️ Time Limit:</strong> {{ total_time_minutes }} minutes
                    </div>
                <div class="test-info-item">
                    <strong>📊 Passing Score:</strong> {{ passing_score }}%
                    </div>
                    </div>

            <!-- Test Content -->
            <div class="test-content">
                <div id="successMessage" class="success-message">
                    <strong>Thank you!</strong> Your valuable time to attempt the test is appreciated.
                </div>
                <div id="errorMessage" class="error-message">
                    <strong>Error!</strong> <span id="errorText"></span>
            </div>

                <!-- Progress Indicator -->
                <div class="progress-indicator">
                    <div class="d-flex justify-content-between align-items-center">
                        <span><strong>Progress:</strong> <span id="progressText">0 of {{ total_questions }}</span> answered</span>
                        <div class="progress" style="width: 60%; height: 10px;">
                            <div id="progressBar" class="progress-bar" role="progressbar" style="width: 0%"></div>
            </div>
        </div>
    </div>

                <form id="aptitudeTestForm">
                    <input type="hidden" name="job_requirement_id" value="{{ job_requirement_id }}">
                    <input type="hidden" name="aptitude_test_id" value="{{ aptitude_test_id }}">

                    {% for question in questions %}
                    <div class="question-card" data-question-id="{{ question.question_id }}">
                        <div>
                            <span class="question-number">Question {{ question.question_number }}</span>
                            <span class="difficulty-badge difficulty-{{ question.difficulty }}">{{ question.difficulty|title }}</span>
                            <span class="category-badge">{{ question.category }}</span>
                            {% if question.tags %}
                                {% for tag in question.tags %}
                                <span class="badge bg-secondary" style="font-size: 0.75rem;">{{ tag }}</span>
                                {% endfor %}
                            {% endif %}
                        </div>
                        
                        <div class="question-text">
                            {{ question.question_text }}
                        </div>

                        <div class="options mt-3">
                            {% for option_key, option_value in question.options.items() %}
                            <label class="option-label d-block">
                                <input type="radio" name="question_{{ question.question_number }}" 
                                       value="{{ option_key }}" 
                                       data-question-id="{{ question.question_id }}"
                                       data-question-number="{{ question.question_number }}"
                                       onchange="updateProgress()" required>
                                <span class="option-text ms-2">
                                    <strong>{{ option_key }}.</strong> {{ option_value }}
                                </span>
                            </label>
                            {% endfor %}
                    </div>
                    </div>
                    {% endfor %}

                    <div class="text-center mt-4">
                        <button type="submit" class="btn btn-primary btn-submit btn-lg">
                            📝 Submit Test
                            </button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <!-- Proctoring Warning Modal -->
    <div class="modal fade warning-modal" id="proctoringModal" tabindex="-1" aria-labelledby="proctoringModalLabel" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="proctoringModalLabel">⚠️ Proctoring Warning</h5>
                </div>
                <div class="modal-body">
                    <p id="warningText">This action is not allowed during the test.</p>
                    <div class="alert alert-danger">
                        <strong>Violation Recorded:</strong> This incident will be reported.
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-danger" data-bs-dismiss="modal">I Understand</button>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Timer functionality
        const totalSeconds = {{ total_time_minutes }} * 60;
        let remainingSeconds = totalSeconds;
        let timerIntervalId = null;
        let timerStartedAt = null;
        let timerEndsAt = null;
        const timerElement = document.getElementById('timeRemaining');
        const timerContainer = document.getElementById('timer');

        function renderTimer() {
            const safe = Math.max(0, remainingSeconds);
            const minutes = Math.floor(safe / 60);
            const seconds = safe % 60;
            const el = timerElement || document.getElementById('timeRemaining');
            if (el) {
                el.textContent = minutes + ':' + seconds.toString().padStart(2, '0');
            }
            const cont = timerContainer || document.getElementById('timer');
            if (cont) {
                if (safe <= 60) {
                    cont.classList.add('danger');
                } else if (safe <= 300) {
                    cont.classList.add('warning');
                }
            }
        }

        function tickTimer() {
            try {
                if (timerEndsAt !== null) {
                    remainingSeconds = Math.ceil((timerEndsAt - Date.now()) / 1000);
                }
                renderTimer();
                if (remainingSeconds <= 0) {
                    if (timerIntervalId !== null) {
                        clearInterval(timerIntervalId);
                        timerIntervalId = null;
                    }
                    alert('Time is up! Submitting your test...');
                    const form = document.getElementById('aptitudeTestForm');
                    if (form) form.submit();
                }
            } catch (err) {
                console.error('Timer tick error:', err);
            }
        }

        // Public alias used elsewhere in the code.
        function updateTimer() { tickTimer(); }

        function startTimer() {
            if (timerStartedAt !== null) return; // idempotent
            timerStartedAt = Date.now();
            timerEndsAt = timerStartedAt + totalSeconds * 1000;
            renderTimer();
            // Kick the first decrement immediately so the user sees movement.
            setTimeout(tickTimer, 1000);
            // Primary loop.
            timerIntervalId = setInterval(tickTimer, 1000);
            console.log('[aptitude] Timer started for', totalSeconds, 'seconds');
        }

        // Auto-start safety net: if for ANY reason startTest is never called
        // (e.g. user dismissed fullscreen, button event lost), the timer must
        // still start as soon as the entry overlay is gone.
        document.addEventListener('visibilitychange', function() {
            if (!document.hidden && timerStartedAt === null) {
                const entry = document.getElementById('fullscreenEntry');
                if (entry && entry.style.display === 'none') startTimer();
            }
        });

        // Timer will be started by startTest() function

        // Progress tracking
        const totalQuestions = {{ total_questions }};
        function updateProgress() {
            const answeredQuestions = document.querySelectorAll('input[type="radio"]:checked').length;
            document.getElementById('progressText').textContent = `${answeredQuestions} of ${totalQuestions}`;
            const progressPercent = (answeredQuestions / totalQuestions) * 100;
            document.getElementById('progressBar').style.width = progressPercent + '%';
        }

        // Form submission
        document.getElementById('aptitudeTestForm').addEventListener('submit', async function(e) {
            e.preventDefault();

            const form = e.target;
            const formData = new FormData(form);
            const submitButton = form.querySelector('button[type="submit"]');

            // Check if all questions are answered
            const answeredQuestions = document.querySelectorAll('input[type="radio"]:checked').length;
            if (answeredQuestions < totalQuestions) {
                if (!confirm(`You have only answered ${answeredQuestions} out of ${totalQuestions} questions. Do you want to submit anyway?`)) {
                    return;
                }
            }

            // Disable proctoring before submission
            disableProctoring();
            
            // Exit fullscreen mode
            if (document.fullscreenElement || document.webkitFullscreenElement || document.msFullscreenElement) {
                exitFullscreen();
            }
            document.body.classList.remove('fullscreen-active');

            // Disable submit button
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Submitting...';

            // Hide previous messages
            document.getElementById('successMessage').style.display = 'none';
            document.getElementById('errorMessage').style.display = 'none';

            // Collect answers (keyed by 0-based question index)
            const answers = {};
            const radioInputs = document.querySelectorAll('input[type="radio"]:checked');
            radioInputs.forEach(input => {
                const questionNumber = parseInt(input.getAttribute('data-question-number'), 10);
                if (!Number.isNaN(questionNumber)) {
                    const indexKey = String(questionNumber - 1);
                    answers[indexKey] = input.value;
                }
            });

            // Prepare submission data
            const attemptKey = `test_attempt_{{ job_requirement_id }}_{{ aptitude_test_id }}`;
            const attemptId = sessionStorage.getItem(attemptKey);
            if (!attemptId) {
                alert('Session expired. Please login again.');
                const loginUrl = `http://localhost:8890/tests/login_{{ job_requirement_id }}_{{ aptitude_test_id }}.html`;
                window.location.replace(loginUrl);
                return;
            }

            const submissionData = {
                attempt_id: attemptId,
                answers: answers,
                time_taken_seconds: totalSeconds - remainingSeconds,
                tab_switches: tabSwitchCount,
                keyboard_violations: keyboardViolationCount
            };

            console.log('Submitting test:', submissionData);

            try {
                // TODO: Replace with actual API endpoint
                const apiEndpoint = 'http://localhost:8888/interview-management-service/api/v1/aptitude/submit-test';
                
                const response = await fetch(apiEndpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(submissionData)
                });

                if (response.ok) {
                    const responseData = await response.json();
                    console.log('Success response:', responseData);
                    
                    // Clear session tokens and saved answers
                    const sessionKey = `test_session_{{ job_requirement_id }}_{{ aptitude_test_id }}`;
                    const attemptKey = `test_attempt_{{ job_requirement_id }}_{{ aptitude_test_id }}`;
                    sessionStorage.removeItem(sessionKey);
                    sessionStorage.removeItem(attemptKey);
                    localStorage.removeItem(answersStorageKey);
                    
                    // Close the tab/window immediately after successful submission
                    window.close();
                } else {
                    const errorData = await response.json().catch(() => ({ detail: 'Unknown error occurred' }));
                    console.log('Error response:', errorData);
                    document.getElementById('errorText').textContent = errorData.detail || 'Failed to submit test';
                    document.getElementById('errorMessage').style.display = 'block';
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                }
            } catch (error) {
                console.error('Submission error:', error);
                document.getElementById('errorText').textContent = 'Network error. Please check your connection and try again.';
                document.getElementById('errorMessage').style.display = 'block';
                window.scrollTo({ top: 0, behavior: 'smooth' });
            } finally {
                submitButton.disabled = false;
                submitButton.innerHTML = '📝 Submit Test';
            }
        });

        // Initialize progress on page load
        updateProgress();

        // Fullscreen mode functionality
        let isFullscreen = false;

        function enterFullscreen() {
            const element = document.documentElement;
            if (element.requestFullscreen) {
                element.requestFullscreen();
            } else if (element.webkitRequestFullscreen) {
                element.webkitRequestFullscreen();
            } else if (element.msRequestFullscreen) {
                element.msRequestFullscreen();
            }
        }

        // Start test button handler
        window.startTest = function() {
            // Enter fullscreen
            enterFullscreen();

            // Hide entry screen and start timer
            setTimeout(() => {
                document.getElementById('fullscreenEntry').style.display = 'none';
                // Start the timer (idempotent)
                startTimer();
            }, 500);

            // Safety net: ensure the timer starts even if the fullscreen
            // transition is slow or the setTimeout above is throttled.
            startTimer();
        }

        function exitFullscreen() {
            if (document.exitFullscreen) {
                document.exitFullscreen();
            } else if (document.webkitExitFullscreen) {
                document.webkitExitFullscreen();
            } else if (document.msExitFullscreen) {
                document.msExitFullscreen();
            }
        }

        function handleFullscreenChange() {
            isFullscreen = !!(document.fullscreenElement || document.webkitFullscreenElement || document.msFullscreenElement);

            if (isFullscreen) {
                document.body.classList.add('fullscreen-active');
                console.log('Entered fullscreen mode');
            } else {
                document.body.classList.remove('fullscreen-active');
                const entryScreen = document.getElementById('fullscreenEntry');
                if (!document.hidden && entryScreen.style.display === 'none') {
                    // User has started test but exited fullscreen
                    showWarning('Exiting fullscreen mode is not allowed during the test.');
                    // Auto re-enter fullscreen
                    setTimeout(() => {
                        enterFullscreen();
                    }, 2000);
                }
                console.log('Exited fullscreen mode');
            }
        }

        // Listen for fullscreen changes
        document.addEventListener('fullscreenchange', handleFullscreenChange);
        document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
        document.addEventListener('msfullscreenchange', handleFullscreenChange);

        // Prevent refresh and show confirmation
        window.addEventListener('beforeunload', function(e) {
                    e.preventDefault();
            e.returnValue = 'Are you sure you want to leave? Your test progress will be lost.';
            return e.returnValue;
        });

        // Answer persistence
        const answersStorageKey = `test_answers_{{ job_requirement_id }}_{{ aptitude_test_id }}`;

        function saveAnswers() {
            const answers = {};
            const radioInputs = document.querySelectorAll('input[type="radio"]:checked');
            radioInputs.forEach(input => {
                const questionNumber = parseInt(input.getAttribute('data-question-number'), 10);
                if (!Number.isNaN(questionNumber)) {
                    answers[questionNumber - 1] = input.value;
                }
            });
            localStorage.setItem(answersStorageKey, JSON.stringify(answers));
        }

        function loadAnswers() {
            const savedAnswers = localStorage.getItem(answersStorageKey);
            if (savedAnswers) {
                const answers = JSON.parse(savedAnswers);
                Object.keys(answers).forEach(index => {
                    const questionNumber = parseInt(index, 10) + 1;
                    const radioInput = document.querySelector(`input[type="radio"][data-question-number="${questionNumber}"][value="${answers[index]}"]`);
                    if (radioInput) {
                        radioInput.checked = true;
                    }
                });
                updateProgress();
            }
        }

        // Auto-save answers every 30 seconds
        setInterval(saveAnswers, 30000);

        // Load saved answers on page load
        window.addEventListener('load', function() {
            loadAnswers();
        });

        // Proctoring: Track violations
        let tabSwitchCount = 0;
        let keyboardViolationCount = 0;
        let proctoringEnabled = true;

        // Tab switching detection
        function handleTabSwitch() {
            if (document.hidden && proctoringEnabled) {
                tabSwitchCount++;
                showWarning('Tab switching is not allowed during the test. Please return to the test window.');
                console.log(`Tab switch violation #${tabSwitchCount}`);
            }
        }
        document.addEventListener('visibilitychange', handleTabSwitch);

        // Keyboard key press detection (excluding input fields)
        function handleKeyPress(event) {
            if (!proctoringEnabled) return;
            
            // Allow typing in input fields, but warn for other keys
            const activeElement = document.activeElement;
            const isInInput = activeElement && (
                activeElement.tagName === 'INPUT' ||
                activeElement.tagName === 'TEXTAREA' ||
                activeElement.contentEditable === 'true'
            );

            if (!isInInput) {
                keyboardViolationCount++;
                showWarning('Using keyboard shortcuts or keys is not allowed during the test.');
                console.log(`Keyboard violation #${keyboardViolationCount}`);
            }
        }
        document.addEventListener('keydown', handleKeyPress);

        // Remove all proctoring
        function disableProctoring() {
            proctoringEnabled = false;
            document.removeEventListener('visibilitychange', handleTabSwitch);
            document.removeEventListener('keydown', handleKeyPress);
            // Hide the fullscreen warning bar
            const warningBar = document.getElementById('fullscreenWarning');
            if (warningBar) {
                warningBar.style.display = 'none';
            }
            console.log('Proctoring disabled');
        }

        // Show warning modal
        function showWarning(message) {
            document.getElementById('warningText').textContent = message;
            const modal = new bootstrap.Modal(document.getElementById('proctoringModal'));
            modal.show();
        }
    </script>
</body>
</html>
"""


@app.route('/interview-management-service/api/v1/aptitude/generate-test/<job_requirement_id>', methods=['POST'])
def generate_test(job_requirement_id):
    """
    Generate both login form and aptitude test form for a specific test.
    
    Accepts POST with combined data in request body containing:
    - test_details: dict with test metadata (includes aptitude_test_id)
    - questions: list of question objects
    - login_data: dict with login form data
    
    Returns JSON response with:
    - success: boolean
    - message: string
    - login_form_url: string (URL to access the login form - entry point)
    - test_form_url: string (URL to access the test form)
    """
    try:
        # Get data from POST request body
        if not request.is_json:
            return jsonify({
                "success": False,
                "message": "Request must be JSON",
                "error": "Invalid content type"
            }), 400

        data = request.get_json()
        test_details = data.get('test_details', {})
        questions = data.get('questions', [])
        login_data = data.get('login_data', {})
        
        if not test_details or not questions:
            return jsonify({
                "success": False,
                "message": "No test data provided",
                "error": "Missing test_details or questions in request body"
            }), 400
        
        # Get aptitude_test_id from test_details
        aptitude_test_id = test_details.get('aptitude_test_id', 'unknown')
        
        logger.info(f"Generating test (login + test form) for job_requirement_id: {job_requirement_id}, test_id: {aptitude_test_id}")
        logger.info(f"Test details: {test_details}")
        logger.info(f"Number of questions: {len(questions)}")
        
        # === Generate Test Form ===
        test_filename = f"{job_requirement_id}_{aptitude_test_id}.html"
        test_file_path = TESTS_DIR / test_filename

        test_template_vars = {
            'job_requirement_id': job_requirement_id,
            'aptitude_test_id': aptitude_test_id,
            'test_title': test_details.get('test_title', 'Aptitude Test'),
            'total_questions': test_details.get('total_questions', len(questions)),
            'total_time_minutes': test_details.get('total_time_minutes', 45),
            'passing_score': test_details.get('passing_score_percentage', 60),
            'questions': questions
        }

        test_html_content = render_template_string(
            APTITUDE_TEST_TEMPLATE,
            **test_template_vars
        )

        with open(test_file_path, 'w', encoding='utf-8') as f:
            f.write(test_html_content)

        test_form_url = f"http://{SERVICE_HOST}:{SERVICE_PORT}/tests/{test_filename}"

        logger.info(f"Generated test form for test ID: {aptitude_test_id}")
        logger.info(f"Test form saved at: {test_file_path}")
        logger.info(f"Test form URL: {test_form_url}")

        # === Generate Login Form ===
        login_filename = f"login_{job_requirement_id}_{aptitude_test_id}.html"
        login_file_path = TESTS_DIR / login_filename

        login_template_vars = {
            'job_requirement_id': job_requirement_id,
            'aptitude_test_id': aptitude_test_id,
            'test_title': login_data.get('test_title', test_details.get('test_title', 'Aptitude Test')),
            'login_instructions': login_data.get('login_instructions', 'Please enter your email and password to access the aptitude test.')
        }

        login_html_content = render_template_string(
            LOGIN_FORM_TEMPLATE,
            **login_template_vars
        )

        with open(login_file_path, 'w', encoding='utf-8') as f:
            f.write(login_html_content)

        login_form_url = f"http://{SERVICE_HOST}:{SERVICE_PORT}/tests/{login_filename}"

        logger.info(f"Generated login form for test ID: {aptitude_test_id}")
        logger.info(f"Login form saved at: {login_file_path}")
        logger.info(f"Login form URL: {login_form_url}")

        # Return JSON response with both form URLs
        return jsonify({
            "success": True,
            "message": "Login form and test form generated successfully",
            "job_requirement_id": job_requirement_id,
            "aptitude_test_id": aptitude_test_id,
            "login_form_url": login_form_url,
            "test_form_url": test_form_url,
            "questions_count": len(questions)
        })

    except Exception as e:
        logger.error(f"Error generating test: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "message": f"Failed to generate aptitude test: {str(e)}",
            "error": str(e)
        }), 500
        

# HTML Template for the login form
LOGIN_FORM_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aptitude Test Login</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            background: white;
            min-height: 100vh;
            padding: 40px 0;
        }
        .login-container {
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            padding: 40px;
            max-width: 500px;
            margin: 0 auto;
        }
        .login-header {
            background: #000;
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 30px;
        }
        .form-control:focus {
            border-color: #000;
            box-shadow: 0 0 0 0.2rem rgba(0, 0, 0, 0.15);
        }
        .btn-login {
            background: #000;
            border: none;
            padding: 12px 30px;
            font-weight: 600;
            transition: transform 0.2s;
        }
        .btn-login:hover {
            background: #333;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
        }
        .success-message, .error-message {
            display: none;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .success-message {
            background: #f0f0f0;
            border: 2px solid #333;
            color: #1a1a1a;
        }
        .error-message {
            background: #fff;
            border: 2px solid #1a1a1a;
            color: #1a1a1a;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="login-container">
            <div class="login-header">
                <h1 class="mb-2">🔐 Test Login</h1>
                <p class="mb-0">{{ test_title }}</p>
            </div>

            <div id="successMessage" class="success-message">
                <strong>Success!</strong> <span id="successText"></span>
            </div>
            <div id="errorMessage" class="error-message">
                <strong>Error!</strong> <span id="errorText"></span>
            </div>

            <form id="loginForm">
                <input type="hidden" id="job_requirement_id" value="{{ job_requirement_id }}">
                <input type="hidden" id="aptitude_test_id" value="{{ aptitude_test_id }}">

                <div class="mb-3">
                    <label for="email" class="form-label">Email Address</label>
                    <input type="email" class="form-control" id="email" name="email" required
                           placeholder="Enter your email">
                </div>

                <div class="mb-4">
                    <label for="password" class="form-label">Password</label>
                    <input type="password" class="form-control" id="password" name="password" required
                           placeholder="Enter your password">
                </div>

                <div class="text-center">
                    <button type="submit" class="btn btn-primary btn-login btn-lg">
                        🔑 Login & Start Test
                    </button>
                </div>
            </form>

            <div class="text-center mt-3">
                <small class="text-muted">{{ login_instructions }}</small>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        document.getElementById('loginForm').addEventListener('submit', async function(e) {
                    e.preventDefault();

            const form = e.target;
            const submitButton = form.querySelector('button[type="submit"]');

            // Get form data
            const loginData = {
                email: document.getElementById('email').value,
                password: document.getElementById('password').value
            };

            // Disable submit button
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Logging in...';

            // Hide previous messages
            document.getElementById('successMessage').style.display = 'none';
            document.getElementById('errorMessage').style.display = 'none';

            try {
                // Call the validation endpoint
                const jobReqId = document.getElementById('job_requirement_id').value;
                const testId = document.getElementById('aptitude_test_id').value;
                const apiEndpoint = `http://localhost:8888/interview-management-service/api/v1/aptitude/validate-login/${jobReqId}/${testId}`;
                const sessionKey = `test_session_${jobReqId}_${testId}`;
                const attemptKey = `test_attempt_${jobReqId}_${testId}`;

                const response = await fetch(apiEndpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(loginData)
                });

                const responseData = await response.json();

                if (response.ok && responseData.success) {
                    // Login successful
                    document.getElementById('successText').textContent = responseData.message;
                    document.getElementById('successMessage').style.display = 'block';

                    // Store session token for this test (per-origin sessionStorage)
                    const sessionToken = responseData.data?.session_token;
                    const attemptId = responseData.data?.attempt_info?.attempt_id;
                    if (sessionToken) {
                        sessionStorage.setItem(sessionKey, sessionToken);
                    }
                    if (attemptId) {
                        sessionStorage.setItem(attemptKey, attemptId);
                    }

                    // Redirect to test form after a short delay (URL without token)
                    setTimeout(() => {
                        const formUrl = responseData.data?.test_form_url;
                        if (formUrl) {
                            window.location.href = formUrl;
                        } else {
                            alert('Test access granted! Redirecting...');
                        }
                    }, 800);

                } else {
                    // Login failed
                    document.getElementById('errorText').textContent =
                        responseData.error_message || responseData.detail || 'Login failed. Please check your credentials.';
                    document.getElementById('errorMessage').style.display = 'block';
                }
            } catch (error) {
                console.error('Login error:', error);
                document.getElementById('errorText').textContent = 'Network error. Please check your connection and try again.';
                document.getElementById('errorMessage').style.display = 'block';
            } finally {
                // Re-enable submit button
                submitButton.disabled = false;
                submitButton.innerHTML = '🔑 Login & Start Test';
            }
        });
    </script>
</body>
</html>
"""


@app.route('/tests/<filename>')
def serve_test(filename):
    """
    Serve a previously generated aptitude test HTML file.
    """
    try:
        return send_from_directory(TESTS_DIR, filename)
    except Exception as e:
        logger.error(f"Error serving test: {str(e)}")
        return f"<h1>Error</h1><p>Test form not found: {filename}</p>", 404


@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.
    """
    return {
        "status": "healthy",
        "service": "aptitude-test-service",
        "tests_directory": str(TESTS_DIR),
        "tests_count": len(list(TESTS_DIR.glob("*.html")))
    }


@app.route('/')
def index():
    """
    Root endpoint with information about the service.
    """
    tests = list(TESTS_DIR.glob("*.html"))
    tests_info = [{"filename": f.name, "test_id": f.stem} for f in tests]
    
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Aptitude Test Service</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {
                background: white;
                min-height: 100vh;
                padding: 40px 0;
            }
            .container {
                background: white;
                border-radius: 15px;
                padding: 40px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            }
            .service-title {
                color: #000;
                margin-bottom: 20px;
            }
            .code-block {
                background: #fafafa;
                border-left: 4px solid #000;
                padding: 15px;
                margin: 15px 0;
                border-radius: 5px;
                overflow-x: auto;
            }
            .badge-custom {
                background: #000;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="service-title">🧠 Aptitude Test Service</h1>
            <p class="lead">Generate and serve aptitude test forms dynamically</p>
            
            <div class="alert alert-info">
                <strong>Status:</strong> <span class="badge badge-custom text-white">Running on Port 8890</span>
            </div>
            
            <h3 class="mt-4">📋 How to Use</h3>
            <div class="code-block">
                <strong>Generate a test form:</strong><br>
                <code>POST http://localhost:8890/interview-management-service/api/v1/aptitude/generate-test-form/{job_requirement_id}</code>
            </div>
            
            <h3 class="mt-4">📊 Generated Tests</h3>
            <p><strong>Total tests generated:</strong> {{ tests_count }}</p>
            
            {% if tests_info %}
            <div class="table-responsive">
                <table class="table table-striped">
                    <thead class="table-dark">
                        <tr>
                            <th>Test ID</th>
                            <th>Filename</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for test in tests_info %}
                        <tr>
                            <td><code>{{ test.test_id }}</code></td>
                            <td>{{ test.filename }}</td>
                            <td>
                                <a href="/tests/{{ test.filename }}" class="btn btn-sm btn-primary" target="_blank">View Test</a>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% else %}
            <div class="alert alert-warning">
                No tests generated yet. Use the API endpoint above to generate your first test!
            </div>
            {% endif %}
            
            <h3 class="mt-4">ℹ️ Service Information</h3>
            <ul>
                <li><strong>Port:</strong> 8890</li>
                <li><strong>Tests Directory:</strong> <code>{{ tests_directory }}</code></li>
                <li><strong>Health Check:</strong> <a href="/health" target="_blank">/health</a></li>
            </ul>
        </div>
    </body>
    </html>
    """
    
    return render_template_string(html, 
                                 tests_count=len(tests),
                                 tests_info=tests_info,
                                 tests_directory=str(TESTS_DIR))


if __name__ == '__main__':
    logger.info("Starting Aptitude Test Service...")
    logger.info(f"Tests will be stored in: {TESTS_DIR}")
    logger.info(f"Service available at: http://{SERVICE_HOST}:{SERVICE_PORT}")
    
    app.run(
        host=SERVICE_HOST,
        port=SERVICE_PORT,
        debug=DEBUG_MODE
    )
