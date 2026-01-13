"""
AI-Powered Aptitude Test Generation Service
This service generates comprehensive aptitude tests based on job requirements.
Port: 8890
"""
import os
import json
import logging
import time
from pathlib import Path
from flask import Flask, render_template_string, request, send_from_directory, jsonify
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
SERVICE_HOST = '0.0.0.0'
SERVICE_PORT = 8890
DEBUG_MODE = True
MAIN_APP_API_ENDPOINT = 'http://localhost:8888/interview-management-service/api/v1'

# Get the directory where this script is located
BASE_DIR = Path(__file__).parent
TESTS_DIR = BASE_DIR / 'tests'
RESULTS_DIR = BASE_DIR / 'results'

# Create directories if they don't exist
TESTS_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

# Import Gemini AI
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
    GEMINI_API_KEY = "AIzaSyDHNd6W382fBzwf_HbPxf70sxG13XE9xgA"
    genai.configure(api_key=GEMINI_API_KEY)
    
    # Configure generation parameters for clean JSON output
    generation_config = {
        "temperature": 0.7,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "application/json",  # Force JSON output
    }
    
    model = genai.GenerativeModel(
        'gemini-2.5-flash',
        generation_config=generation_config
    )
    logger.info("Gemini AI initialized successfully with JSON mode")
except ImportError:
    GEMINI_AVAILABLE = False
    model = None
    logger.warning("Gemini AI not available")
except Exception as e:
    GEMINI_AVAILABLE = False
    model = None
    logger.error(f"Failed to initialize Gemini AI: {str(e)}")


def generate_test_prompt(job_details: dict) -> str:
    """Generate the AI prompt for test creation."""
    
    job_title = job_details.get('title', 'Position')
    department = job_details.get('department', 'General')
    description = job_details.get('description', '')
    requirements = job_details.get('requirements', [])
    experience = job_details.get('experience', {})
    
    # Extract skills
    skills = []
    for req in requirements:
        if isinstance(req, dict):
            skills.append(req.get('skill', ''))
        else:
            skills.append(str(req))
    
    # Get experience level
    exp_level = "mid"
    if experience:
        min_years = experience.get('min_years', 0)
        if min_years == 0:
            exp_level = "entry"
        elif min_years >= 5:
            exp_level = "senior"
    
    prompt = f"""
You are an EXPERT APTITUDE TEST GENERATOR. Create a comprehensive, industry-specific assessment test based on the job requirements provided below.

═══════════════════════════════════════════════════════════════
JOB DETAILS
═══════════════════════════════════════════════════════════════
Position: {job_title}
Department: {department}
Experience Level: {exp_level}
Industry: Technology

Description:
{description}

Required Skills:
{', '.join(skills)}

═══════════════════════════════════════════════════════════════
TEST GENERATION REQUIREMENTS
═══════════════════════════════════════════════════════════════

**MANDATORY STRUCTURE:**
- Generate EXACTLY 30 questions
- Difficulty Distribution:
  * 12 Simple questions (40%) - Basic concepts
  * 12 Medium questions (40%) - Applied reasoning
  * 6 Hard questions (20%) - Advanced logic

**QUESTION FORMAT:**
- All MCQ with 4 options (A, B, C, D)
- Only ONE correct answer
- Include plausible distractors
- Text-based only (no images)

**CONTENT FOCUS:**
- Core Logic (50%): Analytical reasoning, patterns, numerical reasoning
- Critical Thinking (30%): Problem-solving, decision-making
- Domain-Specific (20%): Industry concepts from job requirements

**QUALITY RULES:**
1. Questions MUST be clear and unambiguous
2. Options MUST be plausible (avoid obviously wrong answers)
3. Align with job requirements and skills
4. NO cultural bias or trick questions
5. Each question answerable in allocated time

═══════════════════════════════════════════════════════════════
OUTPUT FORMAT - RETURN ONLY VALID JSON
═══════════════════════════════════════════════════════════════

{{
  "test_metadata": {{
    "test_id": "TEST_{job_title.upper().replace(' ', '_')}_{int(time.time())}",
    "job_title": "{job_title}",
    "industry": "{department}",
    "total_questions": 30,
    "total_time_minutes": 45,
    "passing_score_percentage": 60,
    "difficulty_distribution": {{
      "simple": 12,
      "medium": 12,
      "hard": 6
    }}
  }},
  "proctoring_settings": {{
    "keyboard_tracking": true,
    "tab_switch_detection": true,
    "mouse_tracking": true,
    "copy_paste_detection": true,
    "camera_required": false,
    "microphone_required": false,
    "fullscreen_mode": true,
    "max_tab_switches_allowed": 3,
    "warning_on_suspicious_activity": true
  }},
  "time_allocation": {{
    "simple_question_seconds": 60,
    "medium_question_seconds": 90,
    "hard_question_seconds": 120,
    "total_test_duration_minutes": 45
  }},
  "questions": [
    {{
      "question_id": "q1",
      "question_number": 1,
      "difficulty": "simple",
      "category": "core_logic",
      "question_text": "Question text here",
      "options": {{
        "A": "Option A",
        "B": "Option B",
        "C": "Option C",
        "D": "Option D"
      }},
      "correct_answer": "A",
      "explanation": "Explanation why A is correct",
      "time_allocated_seconds": 60,
      "tags": ["tag1", "tag2"]
    }}
  ]
}}

**CRITICAL JSON FORMATTING RULES:**
- Return ONLY valid JSON (no markdown, no extra text)
- Exactly 30 questions in the array
- Each question must have all required fields
- Correct_answer must be one of: A, B, C, D
- Questions must be relevant to {job_title} role
- Use skills: {', '.join(skills[:5])} in domain-specific questions

**IMPORTANT TEXT FORMATTING:**
- NO line breaks or newline characters (\\n) inside question text or options
- NO special characters like tabs (\\t) or control characters
- Use simple plain text only
- Keep all text on single lines
- Use spaces instead of newlines for formatting
- Replace any code examples with plain text descriptions

Generate the test now!
"""
    
    return prompt


def clean_json_string(text: str) -> str:
    """Clean invalid control characters from JSON string."""
    import re
    # Remove control characters except newlines, tabs, and carriage returns
    # which are valid when properly escaped in JSON
    cleaned = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
    # Replace unescaped newlines in strings with spaces
    # This is a simple approach - more sophisticated would parse JSON structure
    cleaned = cleaned.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    return cleaned


def generate_aptitude_test(job_details: dict) -> dict:
    """Generate aptitude test using AI (synchronous)."""
    try:
        if not GEMINI_AVAILABLE or not model:
            logger.error("Gemini AI not available")
            return None
        
        prompt = generate_test_prompt(job_details)
        
        logger.info(f"Generating test for job: {job_details.get('title')}")
        
        start_time = time.time()
        response = model.generate_content(prompt)
        processing_time = time.time() - start_time
        
        # Parse response
        response_text = response.text.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        # Clean control characters
        response_text = clean_json_string(response_text.strip())
        
        # Log the response for debugging (first 500 chars)
        logger.info(f"AI Response (first 500 chars): {response_text[:500]}")
        
        test_data = json.loads(response_text)
        
        # Print token usage
        print("\n" + "="*70)
        print("🧠 AI TEST GENERATION - TOKEN USAGE")
        print("="*70)
        print(f"📥 Input Tokens:  {response.usage_metadata.prompt_token_count:,}")
        print(f"📤 Output Tokens: {response.usage_metadata.candidates_token_count:,}")
        print(f"📊 Total Tokens:  {response.usage_metadata.total_token_count:,}")
        print(f"⏱️  Processing Time: {processing_time:.2f}s")
        print(f"📝 Questions Generated: {len(test_data.get('questions', []))}")
        print("="*70 + "\n")
        
        logger.info(f"Test generated successfully with {len(test_data.get('questions', []))} questions")
        
        return test_data
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response: {str(e)}")
        logger.error(f"Response length: {len(response_text) if 'response_text' in locals() else 'N/A'}")
        
        # Save problematic response to file for debugging
        try:
            error_file = TESTS_DIR / f"error_response_{int(time.time())}.txt"
            with open(error_file, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write("FAILED AI RESPONSE\n")
                f.write("="*80 + "\n")
                f.write(f"Error: {str(e)}\n")
                f.write("="*80 + "\n")
                if 'response_text' in locals():
                    f.write(response_text)
                else:
                    f.write("Response text not available")
            logger.info(f"Saved error response to: {error_file}")
        except:
            pass
        
        return None
    except Exception as e:
        logger.error(f"Error generating test: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None


# HTML Template for the test interface (will be continued in next message)
TEST_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ test_metadata.job_title }} - Aptitude Test</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px 0;
        }
        .test-container {
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
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
            border-bottom: 2px solid #667eea;
        }
        .question-container {
            padding: 30px;
            display: none;
        }
        .question-container.active {
            display: block;
        }
        .question-text {
            font-size: 1.1rem;
            font-weight: 500;
            margin-bottom: 25px;
            color: #333;
        }
        .option-btn {
            width: 100%;
            text-align: left;
            padding: 15px 20px;
            margin-bottom: 12px;
            border: 2px solid #e9ecef;
            background: white;
            border-radius: 8px;
            transition: all 0.3s;
            cursor: pointer;
        }
        .option-btn:hover {
            border-color: #667eea;
            background: #f8f9fa;
        }
        .option-btn.selected {
            border-color: #667eea;
            background: #e7f1ff;
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
            font-weight: bold;
            color: #667eea;
            z-index: 1000;
        }
        .timer.warning {
            color: #dc3545;
            animation: pulse 1s infinite;
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }
        .navigation-buttons {
            display: flex;
            justify-content: space-between;
            padding: 20px 30px;
            border-top: 1px solid #e9ecef;
        }
        .question-indicator {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            padding: 20px;
            background: #f8f9fa;
        }
        .q-indicator {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            border: 2px solid #dee2e6;
            background: white;
            cursor: pointer;
            font-weight: 500;
        }
        .q-indicator.answered {
            background: #28a745;
            color: white;
            border-color: #28a745;
        }
        .q-indicator.current {
            background: #667eea;
            color: white;
            border-color: #667eea;
        }
        .proctoring-warning {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: #dc3545;
            color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.5);
            display: none;
            z-index: 2000;
            text-align: center;
        }
        .difficulty-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85rem;
            font-weight: 600;
        }
        .difficulty-simple {
            background: #d4edda;
            color: #155724;
        }
        .difficulty-medium {
            background: #fff3cd;
            color: #856404;
        }
        .difficulty-hard {
            background: #f8d7da;
            color: #721c24;
        }
    </style>
</head>
<body>
    <div class="timer" id="timer">45:00</div>
    
    <div class="proctoring-warning" id="proctoringWarning">
        <h4>⚠️ Suspicious Activity Detected</h4>
        <p>Please stay on this page. Tab switches remaining: <span id="tabSwitchCount">3</span></p>
        <button class="btn btn-light" onclick="closeWarning()">Continue Test</button>
    </div>

    <div class="container">
        <div class="test-container">
            <div class="test-header">
                <h1>{{ test_metadata.job_title }}</h1>
                <p class="mb-0">Aptitude Assessment Test</p>
            </div>

            <div class="test-info">
                <div class="row">
                    <div class="col-md-3">
                        <strong>Total Questions:</strong> {{ test_metadata.total_questions }}
                    </div>
                    <div class="col-md-3">
                        <strong>Duration:</strong> {{ test_metadata.total_time_minutes }} minutes
                    </div>
                    <div class="col-md-3">
                        <strong>Passing Score:</strong> {{ test_metadata.passing_score_percentage }}%
                    </div>
                    <div class="col-md-3">
                        <strong>Question Type:</strong> MCQ
                    </div>
                </div>
            </div>

            <div class="question-indicator" id="questionIndicator"></div>

            <div id="questionsContainer"></div>

            <div class="navigation-buttons">
                <button class="btn btn-secondary" id="prevBtn" onclick="previousQuestion()">← Previous</button>
                <button class="btn btn-primary" id="nextBtn" onclick="nextQuestion()">Next →</button>
                <button class="btn btn-success" id="submitBtn" onclick="submitTest()" style="display:none;">Submit Test</button>
            </div>
        </div>
    </div>

    <script>
        const testData = {{ test_data_json | safe }};
        let currentQuestion = 0;
        let answers = {};
        let timeRemaining = {{ test_metadata.total_time_minutes }} * 60; // in seconds
        let tabSwitches = 0;
        let maxTabSwitches = {{ proctoring_settings.max_tab_switches_allowed }};
        let proctoring = {{ proctoring_settings_json | safe }};
        
        // Initialize test
        function initializeTest() {
            renderQuestions();
            renderIndicators();
            startTimer();
            setupProctoring();
            showQuestion(0);
        }

        function renderQuestions() {
            const container = document.getElementById('questionsContainer');
            testData.questions.forEach((q, index) => {
                const questionDiv = document.createElement('div');
                questionDiv.className = 'question-container';
                questionDiv.id = `question-${index}`;
                
                questionDiv.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h4>Question ${q.question_number} of ${testData.questions.length}</h4>
                        <span class="difficulty-badge difficulty-${q.difficulty}">${q.difficulty.toUpperCase()}</span>
                    </div>
                    <div class="question-text">${q.question_text}</div>
                    <div class="options">
                        ${Object.entries(q.options).map(([key, value]) => `
                            <button class="option-btn" data-question="${index}" data-option="${key}" onclick="selectOption(${index}, '${key}')">
                                <strong>${key}.</strong> ${value}
                            </button>
                        `).join('')}
                    </div>
                `;
                
                container.appendChild(questionDiv);
            });
        }

        function renderIndicators() {
            const container = document.getElementById('questionIndicator');
            testData.questions.forEach((q, index) => {
                const indicator = document.createElement('div');
                indicator.className = 'q-indicator';
                indicator.id = `indicator-${index}`;
                indicator.textContent = index + 1;
                indicator.onclick = () => showQuestion(index);
                container.appendChild(indicator);
            });
        }

        function showQuestion(index) {
            document.querySelectorAll('.question-container').forEach(q => q.classList.remove('active'));
            document.querySelectorAll('.q-indicator').forEach(i => i.classList.remove('current'));
            
            document.getElementById(`question-${index}`).classList.add('active');
            document.getElementById(`indicator-${index}`).classList.add('current');
            
            currentQuestion = index;
            
            // Update navigation buttons
            document.getElementById('prevBtn').style.display = index === 0 ? 'none' : 'block';
            document.getElementById('nextBtn').style.display = index === testData.questions.length - 1 ? 'none' : 'block';
            document.getElementById('submitBtn').style.display = index === testData.questions.length - 1 ? 'block' : 'none';
            
            // Restore selected answer
            if (answers[index]) {
                document.querySelectorAll(`[data-question="${index}"]`).forEach(btn => {
                    if (btn.dataset.option === answers[index]) {
                        btn.classList.add('selected');
                    }
                });
            }
        }

        function selectOption(questionIndex, option) {
            // Clear previous selection
            document.querySelectorAll(`[data-question="${questionIndex}"]`).forEach(btn => {
                btn.classList.remove('selected');
            });
            
            // Mark new selection
            event.target.closest('.option-btn').classList.add('selected');
            
            // Save answer
            answers[questionIndex] = option;
            
            // Update indicator
            document.getElementById(`indicator-${questionIndex}`).classList.add('answered');
        }

        function nextQuestion() {
            if (currentQuestion < testData.questions.length - 1) {
                showQuestion(currentQuestion + 1);
            }
        }

        function previousQuestion() {
            if (currentQuestion > 0) {
                showQuestion(currentQuestion - 1);
            }
        }

        function startTimer() {
            setInterval(() => {
                if (timeRemaining > 0) {
                    timeRemaining--;
                    const minutes = Math.floor(timeRemaining / 60);
                    const seconds = timeRemaining % 60;
                    document.getElementById('timer').textContent = 
                        `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
                    
                    if (timeRemaining < 300) { // Last 5 minutes
                        document.getElementById('timer').classList.add('warning');
                    }
                } else {
                    submitTest();
                }
            }, 1000);
        }

        function setupProctoring() {
            if (proctoring.tab_switch_detection) {
                document.addEventListener('visibilitychange', () => {
                    if (document.hidden) {
                        tabSwitches++;
                        document.getElementById('tabSwitchCount').textContent = maxTabSwitches - tabSwitches;
                        document.getElementById('proctoringWarning').style.display = 'block';
                        
                        if (tabSwitches >= maxTabSwitches) {
                            alert('Maximum tab switches exceeded. Test will be submitted automatically.');
                            submitTest();
                        }
                    }
                });
            }
            
            if (proctoring.copy_paste_detection) {
                document.addEventListener('copy', (e) => {
                    e.preventDefault();
                    console.log('Copy detected and blocked');
                });
                
                document.addEventListener('paste', (e) => {
                    e.preventDefault();
                    console.log('Paste detected and blocked');
                });
            }
            
            if (proctoring.fullscreen_mode) {
                document.documentElement.requestFullscreen();
            }
        }

        function closeWarning() {
            document.getElementById('proctoringWarning').style.display = 'none';
        }

        function submitTest() {
            const answeredCount = Object.keys(answers).length;
            const totalQuestions = testData.questions.length;
            
            if (answeredCount < totalQuestions) {
                if (!confirm(`You have answered ${answeredCount} out of ${totalQuestions} questions. Submit anyway?`)) {
                    return;
                }
            }
            
            // Calculate score
            let correctAnswers = 0;
            testData.questions.forEach((q, index) => {
                if (answers[index] === q.correct_answer) {
                    correctAnswers++;
                }
            });
            
            const scorePercentage = (correctAnswers / totalQuestions * 100).toFixed(2);
            const passed = scorePercentage >= testData.test_metadata.passing_score_percentage;
            
            // Show results
            alert(`Test Submitted!\\n\\nCorrect Answers: ${correctAnswers}/${totalQuestions}\\nScore: ${scorePercentage}%\\nStatus: ${passed ? 'PASSED ✅' : 'FAILED ❌'}`);
            
            // TODO: Send results to server
            console.log('Test Results:', {
                answers,
                correctAnswers,
                scorePercentage,
                passed,
                tabSwitches
            });
        }

        // Initialize on load
        initializeTest();
    </script>
</body>
</html>
"""


@app.route('/interview-management-service/api/v1/tests/generate/<job_requirement_id>', methods=['GET', 'POST'])
def generate_test(job_requirement_id):
    """Generate aptitude test for a job requirement."""
    try:
        logger.info(f"Generating test for job_requirement_id: {job_requirement_id}")
        
        # Get job details from request body (sent by FastAPI)
        job_details = {}
        if request.method == 'POST' and request.is_json:
            data = request.get_json()
            job_details = data.get('job_details', {})
        
        if not job_details:
            return jsonify({
                "success": False,
                "message": "Job details not provided",
                "error": "Missing job_details in request body"
            }), 400
        
        # Generate test using AI
        test_data = generate_aptitude_test(job_details)
        
        if not test_data:
            return jsonify({
                "success": False,
                "message": "Failed to generate test",
                "error": "AI generation failed"
            }), 500
        
        # Save test HTML
        safe_filename = f"{job_requirement_id}.html"
        test_file_path = TESTS_DIR / safe_filename
        
        html_content = render_template_string(
            TEST_TEMPLATE,
            test_metadata=test_data['test_metadata'],
            proctoring_settings=test_data['proctoring_settings'],
            test_data_json=json.dumps(test_data),
            proctoring_settings_json=json.dumps(test_data['proctoring_settings'])
        )
        
        with open(test_file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Generate test URL
        test_url = f"http://{SERVICE_HOST}:{SERVICE_PORT}/tests/{job_requirement_id}.html"
        
        logger.info(f"Test generated successfully: {test_url}")
        
        return jsonify({
            "success": True,
            "message": "Aptitude test generated successfully",
            "job_requirement_id": job_requirement_id,
            "test_url": test_url,
            "test_path": str(test_file_path),
            "test_metadata": test_data['test_metadata']
        })
        
    except Exception as e:
        logger.error(f"Error generating test: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "message": f"Failed to generate test: {str(e)}",
            "error": str(e)
        }), 500


@app.route('/tests/<filename>')
def serve_test(filename):
    """Serve a generated test HTML file."""
    try:
        return send_from_directory(TESTS_DIR, filename)
    except Exception as e:
        logger.error(f"Error serving test: {str(e)}")
        return f"<h1>Error</h1><p>Test not found: {filename}</p>", 404


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "aptitude-test-service",
        "port": SERVICE_PORT,
        "tests_directory": str(TESTS_DIR),
        "tests_count": len(list(TESTS_DIR.glob("*.html"))),
        "ai_available": GEMINI_AVAILABLE
    })


@app.route('/')
def index():
    """Root endpoint with service information."""
    tests = list(TESTS_DIR.glob("*.html"))
    tests_info = [{"filename": f.name, "job_id": f.stem} for f in tests]
    
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
            .badge-custom {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="service-title">🧠 AI-Powered Aptitude Test Service</h1>
            <p class="lead">Generate comprehensive aptitude tests based on job requirements</p>
            
            <div class="alert alert-info">
                <strong>Status:</strong> <span class="badge badge-custom text-white">Running on Port 8890</span>
            </div>
            
            <h3 class="mt-4">📊 Service Information</h3>
            <ul>
                <li><strong>Port:</strong> 8890</li>
                <li><strong>Tests Directory:</strong> <code>{{ tests_directory }}</code></li>
                <li><strong>AI Status:</strong> {{ 'Available ✅' if ai_available else 'Not Available ❌' }}</li>
                <li><strong>Generated Tests:</strong> {{ tests_count }}</li>
            </ul>
            
            <h3 class="mt-4">📋 Generated Tests</h3>
            {% if tests_info %}
            <div class="table-responsive">
                <table class="table table-striped">
                    <thead class="table-dark">
                        <tr>
                            <th>Job Requirement ID</th>
                            <th>Filename</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for test in tests_info %}
                        <tr>
                            <td><code>{{ test.job_id }}</code></td>
                            <td>{{ test.filename }}</td>
                            <td>
                                <a href="/tests/{{ test.filename }}" class="btn btn-sm btn-primary" target="_blank">Take Test</a>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% else %}
            <div class="alert alert-warning">
                No tests generated yet!
            </div>
            {% endif %}
        </div>
    </body>
    </html>
    """
    
    return render_template_string(html, 
                                 tests_count=len(tests),
                                 tests_info=tests_info,
                                 tests_directory=str(TESTS_DIR),
                                 ai_available=GEMINI_AVAILABLE)


if __name__ == '__main__':
    logger.info("Starting AI-Powered Aptitude Test Service...")
    logger.info(f"Tests will be stored in: {TESTS_DIR}")
    logger.info(f"Service available at: http://{SERVICE_HOST}:{SERVICE_PORT}")
    
    app.run(
        host=SERVICE_HOST,
        port=SERVICE_PORT,
        debug=DEBUG_MODE,
        threaded=True
    )

