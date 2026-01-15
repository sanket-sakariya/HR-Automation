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
SERVICE_HOST = '0.0.0.0'
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
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .test-info {
            background: #f8f9fa;
            padding: 20px;
            border-bottom: 3px solid #667eea;
        }
        .test-info-item {
            display: inline-block;
            margin: 0 15px;
        }
        .test-content {
            padding: 30px;
        }
        .question-card {
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 20px;
            margin-bottom: 25px;
            border-radius: 8px;
        }
        .question-number {
            background: #667eea;
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
            color: #333;
            margin: 15px 0;
        }
        .difficulty-badge {
            font-size: 0.85rem;
            padding: 4px 10px;
            border-radius: 12px;
            margin-left: 10px;
        }
        .difficulty-simple {
            background: #28a745;
            color: white;
        }
        .difficulty-medium {
            background: #ffc107;
            color: #333;
        }
        .difficulty-hard {
            background: #dc3545;
            color: white;
        }
        .category-badge {
            background: #6c757d;
            color: white;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.85rem;
            margin-left: 5px;
        }
        .option-label {
            cursor: pointer;
            padding: 12px;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            margin: 8px 0;
            transition: all 0.2s;
        }
        .option-label:hover {
            background: #f8f9fa;
            border-color: #667eea;
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
            color: #667eea;
        }
        .timer.warning {
            background: #fff3cd;
            color: #856404;
        }
        .timer.danger {
            background: #f8d7da;
            color: #721c24;
            animation: pulse 1s infinite;
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }
        .btn-submit {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            padding: 12px 40px;
            font-weight: 600;
            transition: transform 0.2s;
        }
        .btn-submit:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        .progress-indicator {
            padding: 15px 30px;
            background: white;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .success-message, .error-message {
            display: none;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .success-message {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        .error-message {
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
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
                    <strong>Success!</strong> Your test has been submitted successfully.
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

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Timer functionality
        const totalSeconds = {{ total_time_minutes }} * 60;
        let remainingSeconds = totalSeconds;
        const timerElement = document.getElementById('timeRemaining');
        const timerContainer = document.getElementById('timer');

        function updateTimer() {
            const minutes = Math.floor(remainingSeconds / 60);
            const seconds = remainingSeconds % 60;
            timerElement.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;

            if (remainingSeconds <= 60) {
                timerContainer.classList.add('danger');
            } else if (remainingSeconds <= 300) {
                timerContainer.classList.add('warning');
            }

            if (remainingSeconds <= 0) {
                alert('Time is up! Submitting your test...');
                document.getElementById('aptitudeTestForm').submit();
            }

            remainingSeconds--;
        }

        // Start timer
        setInterval(updateTimer, 1000);

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

            // Disable submit button
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Submitting...';

            // Hide previous messages
            document.getElementById('successMessage').style.display = 'none';
            document.getElementById('errorMessage').style.display = 'none';

            // Collect answers
            const answers = {};
            const radioInputs = document.querySelectorAll('input[type="radio"]:checked');
            radioInputs.forEach(input => {
                const questionId = input.getAttribute('data-question-id');
                answers[questionId] = input.value;
            });

            // Prepare submission data
            const submissionData = {
                job_requirement_id: formData.get('job_requirement_id'),
                aptitude_test_id: formData.get('aptitude_test_id'),
                answers: answers,
                time_taken_seconds: totalSeconds - remainingSeconds
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
                    document.getElementById('successMessage').style.display = 'block';
                    form.reset();
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                    
                    // Optionally redirect to results page
                    setTimeout(() => {
                        alert('Test submitted successfully! Thank you for taking the test.');
                    }, 1000);
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
    </script>
</body>
</html>
"""


@app.route('/interview-management-service/api/v1/aptitude/generate-test-form/<job_requirement_id>/<aptitude_test_id>', methods=['POST'])
def generate_test_form(job_requirement_id, aptitude_test_id):
    """
    Generate an aptitude test form for a specific test.
    
    Accepts POST with test_data in request body containing:
    - test_details: dict with test metadata
    - questions: list of question objects
    
    Returns JSON response with:
    - success: boolean
    - message: string
    - form_url: string (URL to access the generated form)
    - form_path: string (local file path)
    """
    try:
        # Get test data from POST request body
        if not request.is_json:
            return jsonify({
                "success": False,
                "message": "Request must be JSON",
                "error": "Invalid content type"
            }), 400
        
        data = request.get_json()
        test_data = data.get('test_data', {})
        
        if not test_data:
            return jsonify({
                "success": False,
                "message": "No test data provided",
                "error": "Missing test_data in request body"
            }), 400
        
        test_details = test_data.get('test_details', {})
        questions = test_data.get('questions', [])
        
        logger.info(f"Generating test form for job_requirement_id: {job_requirement_id}, test_id: {aptitude_test_id}")
        logger.info(f"Test details: {test_details}")
        logger.info(f"Number of questions: {len(questions)}")
        
        # Sanitize the filename
        safe_filename = f"{job_requirement_id}_{aptitude_test_id}.html"
        form_file_path = TESTS_DIR / safe_filename

        # Prepare template variables
        template_vars = {
            'job_requirement_id': job_requirement_id,
            'aptitude_test_id': aptitude_test_id,
            'test_title': test_details.get('test_title', 'Aptitude Test'),
            'total_questions': test_details.get('total_questions', len(questions)),
            'total_time_minutes': test_details.get('total_time_minutes', 45),
            'passing_score': test_details.get('passing_score_percentage', 60),
            'questions': questions
        }

        # Create the HTML content
        html_content = render_template_string(
            APTITUDE_TEST_TEMPLATE,
            **template_vars
        )

        # Save the HTML file to the tests directory
        with open(form_file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        # Generate the URL to access the form
        form_url = f"http://{SERVICE_HOST}:{SERVICE_PORT}/tests/{safe_filename}"

        logger.info(f"Generated test form for test ID: {aptitude_test_id}")
        logger.info(f"Form saved at: {form_file_path}")
        logger.info(f"Form URL: {form_url}")

        # Return JSON response with the form URL
        return jsonify({
            "success": True,
            "message": "Aptitude test form generated successfully",
            "job_requirement_id": job_requirement_id,
            "aptitude_test_id": aptitude_test_id,
            "form_url": form_url,
            "form_path": str(form_file_path),
            "questions_count": len(questions)
        })

    except Exception as e:
        logger.error(f"Error generating test form: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "message": f"Failed to generate aptitude test form: {str(e)}",
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
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 30px;
        }
        .form-control:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.25);
        }
        .btn-login {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            padding: 12px 30px;
            font-weight: 600;
            transition: transform 0.2s;
        }
        .btn-login:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        .success-message, .error-message {
            display: none;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .success-message {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        .error-message {
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
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
                    if (sessionToken) {
                        sessionStorage.setItem(sessionKey, sessionToken);
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


@app.route('/interview-management-service/api/v1/aptitude/generate-login-form/<job_requirement_id>/<aptitude_test_id>', methods=['POST'])
def generate_login_form(job_requirement_id, aptitude_test_id):
    """
    Generate a login form for aptitude test access.

    Accepts POST with login_data in request body to include test information on the form.

    Returns JSON response with:
    - success: boolean
    - message: string
    - form_url: string (URL to access the generated login form)
    - form_path: string (local file path)
    """
    try:
        # Get login data from POST request body
        if not request.is_json:
            return jsonify({
                "success": False,
                "message": "Request must be JSON",
                "error": "Invalid content type"
            }), 400

        data = request.get_json()
        login_data = data.get('login_data', {})

        if not login_data:
            return jsonify({
                "success": False,
                "message": "No login data provided",
                "error": "Missing login_data in request body"
            }), 400

        logger.info(f"Generating login form for job_requirement_id: {job_requirement_id}, test_id: {aptitude_test_id}")

        # Sanitize the filename
        safe_filename = f"login_{job_requirement_id}_{aptitude_test_id}.html"
        form_file_path = TESTS_DIR / safe_filename

        # Prepare template variables
        template_vars = {
            'job_requirement_id': job_requirement_id,
            'aptitude_test_id': aptitude_test_id,
            'test_title': login_data.get('test_title', 'Aptitude Test'),
            'login_instructions': login_data.get('login_instructions', 'Please enter your email and password to access the aptitude test.')
        }

        # Create the HTML content
        html_content = render_template_string(
            LOGIN_FORM_TEMPLATE,
            **template_vars
        )

        # Save the HTML file to the tests directory
        with open(form_file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        # Generate the URL to access the form
        form_url = f"http://{SERVICE_HOST}:{SERVICE_PORT}/tests/{safe_filename}"

        logger.info(f"Generated login form for test ID: {aptitude_test_id}")
        logger.info(f"Login form saved at: {form_file_path}")
        logger.info(f"Login form URL: {form_url}")

        # Return JSON response with the form URL
        return jsonify({
            "success": True,
            "message": "Login form generated successfully",
            "job_requirement_id": job_requirement_id,
            "aptitude_test_id": aptitude_test_id,
            "form_url": form_url,
            "form_path": str(form_file_path)
        })

    except Exception as e:
        logger.error(f"Error generating login form: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "message": f"Failed to generate login form: {str(e)}",
            "error": str(e)
        }), 500


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
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
                color: #667eea;
                margin-bottom: 20px;
            }
            .code-block {
                background: #f8f9fa;
                border-left: 4px solid #667eea;
                padding: 15px;
                margin: 15px 0;
                border-radius: 5px;
                overflow-x: auto;
            }
            .badge-custom {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
                <code>POST http://localhost:8890/interview-management-service/api/v1/aptitude/generate-test-form/{job_requirement_id}/{aptitude_test_id}</code>
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
