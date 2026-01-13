"""
Dynamic Form Flask Service
This service generates and serves HTML forms for job applications.
It has no database access and uses the main app's API endpoint.
"""
import os
import logging
from pathlib import Path
from flask import Flask, render_template_string, request, redirect, url_for, send_from_directory, jsonify

# Import configuration
try:
    from config import (
        SERVICE_HOST, SERVICE_PORT, DEBUG_MODE, MAIN_APP_API_ENDPOINT,
        FORMS_DIRECTORY_NAME, LOG_LEVEL, LOG_FORMAT, FORM_TITLE,
        BOOTSTRAP_CSS_CDN, BOOTSTRAP_JS_CDN
    )
except ImportError:
    # Fallback to default values if config.py is not found
    SERVICE_HOST = '0.0.0.0'
    SERVICE_PORT = 8888
    DEBUG_MODE = True
    MAIN_APP_API_ENDPOINT = 'http://localhost:8888/interview-management-service/api/v1/candidates/apply'
    FORMS_DIRECTORY_NAME = 'forms'
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    FORM_TITLE = 'Job Application Form'
    BOOTSTRAP_CSS_CDN = 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css'
    BOOTSTRAP_JS_CDN = 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js'

# Configure logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL), format=LOG_FORMAT)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Get the directory where this script is located
BASE_DIR = Path(__file__).parent
FORMS_DIR = BASE_DIR / FORMS_DIRECTORY_NAME

# Create forms directory if it doesn't exist
FORMS_DIR.mkdir(exist_ok=True)

# HTML Template for the application form
FORM_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ job_title }} - Job Application</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 0;
        }
        .form-container {
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            padding: 0;
            max-width: 900px;
            margin: 0 auto;
            overflow: hidden;
        }
        .job-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .job-details-section {
            background: #f8f9fa;
            padding: 25px;
            border-bottom: 3px solid #667eea;
        }
        .job-detail-item {
            margin-bottom: 15px;
        }
        .job-detail-label {
            font-weight: 600;
            color: #495057;
            display: inline-block;
            min-width: 120px;
        }
        .requirements-list {
            list-style: none;
            padding-left: 0;
        }
        .requirements-list li {
            padding: 8px 0;
            border-bottom: 1px solid #e9ecef;
        }
        .skill-badge {
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 0.85rem;
            margin-right: 8px;
        }
        .skill-badge.required {
            background: #dc3545;
        }
        .skill-badge.advanced {
            background: #28a745;
        }
        .skill-badge.intermediate {
            background: #ffc107;
            color: #333;
        }
        .form-section {
            padding: 30px;
        }
        .form-label {
            font-weight: 600;
            color: #333;
        }
        .required-field::after {
            content: " *";
            color: #dc3545;
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
        .form-control:focus, .form-select:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.25);
        }
        .success-message {
            display: none;
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .error-message {
            display: none;
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="form-container">
            <!-- Job Header -->
            <div class="job-header">
                <h1 class="mb-2">{{ job_title }}</h1>
                <p class="mb-1"><strong>{{ job_department }}</strong> Department</p>
                <p class="mb-0"><i class="bi bi-geo-alt"></i> {{ job_location }}</p>
            </div>

            <!-- Job Details Section -->
            {% if has_job_details %}
            <div class="job-details-section">
                <h4 class="mb-3" style="color: #667eea;">📋 Job Details</h4>
                
                <div class="job-detail-item">
                    <span class="job-detail-label">Description:</span>
                    <p class="mb-0">{{ job_description }}</p>
                </div>

                {% if job_type %}
                <div class="job-detail-item">
                    <span class="job-detail-label">Job Type:</span>
                    <span class="badge bg-primary">{{ job_type }}</span>
                </div>
                {% endif %}

                {% if salary_range %}
                <div class="job-detail-item">
                    <span class="job-detail-label">Salary Range:</span>
                    <span>{{ salary_range.get('currency', 'INR') }} {{ "{:,}".format(salary_range.get('min', 0)) }} - {{ "{:,}".format(salary_range.get('max', 0)) }}</span>
                </div>
                {% endif %}

                {% if experience %}
                <div class="job-detail-item">
                    <span class="job-detail-label">Experience:</span>
                    <span>{{ experience.get('min_years', 0) }} - {{ experience.get('max_years', 0) }} years</span>
                </div>
                {% endif %}

                {% if requirements %}
                <div class="job-detail-item">
                    <span class="job-detail-label">Required Skills:</span>
                    <div class="mt-2">
                        {% for req in requirements %}
                            <span class="skill-badge {{ req.level }} {% if req.required %}required{% endif %}">
                                {{ req.skill }} ({{ req.level }}){% if req.required %} *{% endif %}
                            </span>
                        {% endfor %}
                    </div>
                </div>
                {% endif %}

                {% if benefits %}
                <div class="job-detail-item">
                    <span class="job-detail-label">Benefits:</span>
                    <ul class="mt-2 mb-0">
                        {% for benefit in benefits %}
                            <li>{{ benefit }}</li>
                        {% endfor %}
                    </ul>
                </div>
                {% endif %}
            </div>
            {% endif %}

            <!-- Form Section -->
            <div class="form-section">
                <div id="successMessage" class="success-message">
                    <strong>Success!</strong> Your application has been submitted successfully.
                </div>
                <div id="errorMessage" class="error-message">
                    <strong>Error!</strong> <span id="errorText"></span>
                </div>

                <form id="applicationForm" action="{{ api_endpoint }}" method="POST" enctype="multipart/form-data">
                <input type="hidden" name="job_requirement_id" value="{{ job_requirement_id }}">

                <!-- Personal Information Section -->
                <div class="mb-4">
                    <h5 class="text-primary mb-3">Personal Information</h5>
                    
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <label for="first_name" class="form-label required-field">First Name</label>
                            <input type="text" class="form-control" id="first_name" name="first_name" required>
                        </div>
                        <div class="col-md-6">
                            <label for="last_name" class="form-label required-field">Last Name</label>
                            <input type="text" class="form-control" id="last_name" name="last_name" required>
                        </div>
                    </div>

                    <div class="row mb-3">
                        <div class="col-md-6">
                            <label for="email" class="form-label required-field">Email</label>
                            <input type="email" class="form-control" id="email" name="email" required>
                        </div>
                        <div class="col-md-6">
                            <label for="phone" class="form-label">Phone</label>
                            <input type="tel" class="form-control" id="phone" name="phone">
                        </div>
                    </div>
                </div>

                <!-- Professional Information Section -->
                <div class="mb-4">
                    <h5 class="text-primary mb-3">Professional Information</h5>
                    
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <label for="linkedin_url" class="form-label">LinkedIn URL</label>
                            <input type="url" class="form-control" id="linkedin_url" name="linkedin_url" placeholder="https://linkedin.com/in/yourprofile">
                        </div>
                        <div class="col-md-6">
                            <label for="portfolio_url" class="form-label">Portfolio URL</label>
                            <input type="url" class="form-control" id="portfolio_url" name="portfolio_url" placeholder="https://yourportfolio.com">
                        </div>
                    </div>

                    <div class="mb-3">
                        <label for="skills" class="form-label">Skills (comma-separated)</label>
                        <input type="text" class="form-control" id="skills" name="skills" placeholder="Python, JavaScript, React, etc.">
                        <small class="text-muted">Enter your skills separated by commas</small>
                    </div>

                    <div class="mb-3">
                        <label for="resume" class="form-label required-field">Resume (PDF)</label>
                        <input type="file" class="form-control" id="resume" name="resume" accept=".pdf" required>
                        <small class="text-muted">Please upload your resume in PDF format</small>
                    </div>
                </div>

                <!-- Location & Preferences Section -->
                <div class="mb-4">
                    <h5 class="text-primary mb-3">Location & Preferences</h5>
                    
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <label for="current_location" class="form-label">Current Location</label>
                            <input type="text" class="form-control" id="current_location" name="current_location" placeholder="City, Country">
                        </div>
                        <div class="col-md-6">
                            <label for="willing_to_relocate" class="form-label">Willing to Relocate?</label>
                            <select class="form-select" id="willing_to_relocate" name="willing_to_relocate">
                                <option value="">Select an option</option>
                                <option value="true">Yes</option>
                                <option value="false">No</option>
                            </select>
                        </div>
                    </div>

                    <div class="row mb-3">
                        <div class="col-md-6">
                            <label for="expected_salary" class="form-label">Expected Salary (Annual)</label>
                            <input type="number" class="form-control" id="expected_salary" name="expected_salary" placeholder="50000">
                        </div>
                        <div class="col-md-6">
                            <label for="notice_period" class="form-label">Notice Period</label>
                            <input type="text" class="form-control" id="notice_period" name="notice_period" placeholder="e.g., 2 weeks, 1 month">
                        </div>
                    </div>
                </div>

                <div class="text-center mt-4">
                    <button type="submit" class="btn btn-primary btn-submit">Submit Application</button>
                </div>
                </form>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        document.getElementById('applicationForm').addEventListener('submit', async function(e) {
            e.preventDefault();

            console.log('Form submission started');

            const form = e.target;
            const formData = new FormData(form);
            const submitButton = form.querySelector('button[type="submit"]');

            // Disable submit button
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Submitting...';

            // Hide previous messages
            document.getElementById('successMessage').style.display = 'none';
            document.getElementById('errorMessage').style.display = 'none';

            console.log('Form action:', form.action);
            console.log('Form data entries:');
            for (let [key, value] of formData.entries()) {
                console.log(key, ':', value instanceof File ? `File(${value.name}, ${value.size} bytes)` : value);
            }

            try {
                console.log('Making fetch request...');
                const response = await fetch(form.action, {
                    method: 'POST',
                    body: formData
                });

                console.log('Response received:', response.status, response.statusText);
                console.log('Response headers:', Object.fromEntries(response.headers.entries()));

                if (response.ok) {
                    console.log('Response OK, attempting to parse JSON...');
                    try {
                        const responseData = await response.json();
                        console.log('Success response data:', responseData);
                    } catch (jsonError) {
                        console.log('Could not parse success response as JSON:', jsonError);
                        // This is OK for success responses
                    }

                    // Show success message
                    console.log('Showing success message');
                    document.getElementById('successMessage').style.display = 'block';
                    form.reset();

                    // Scroll to top
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                } else {
                    console.log('Response not OK, attempting to parse error...');
                    const errorData = await response.json().catch(() => ({ detail: 'Unknown error occurred' }));
                    console.log('Error response data:', errorData);
                    document.getElementById('errorText').textContent = errorData.detail || 'Failed to submit application';
                    document.getElementById('errorMessage').style.display = 'block';
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                }
            } catch (error) {
                console.error('Fetch error:', error);
                console.error('Error type:', error.constructor.name);
                console.error('Error message:', error.message);
                console.error('Error stack:', error.stack);
                document.getElementById('errorText').textContent = 'Network error. Please check your connection and try again.';
                document.getElementById('errorMessage').style.display = 'block';
                window.scrollTo({ top: 0, behavior: 'smooth' });
            } finally {
                // Re-enable submit button
                submitButton.disabled = false;
                submitButton.innerHTML = 'Submit Application';
            }
        });
    </script>
</body>
</html>
"""


@app.route('/interview-management-service/api/v1/candidates/apply/<job_requirement_id>', methods=['GET', 'POST'])
def get_application_form(job_requirement_id):
    """
    Generate a form for a specific job requirement ID and return the URL to access it.
    Creates an HTML file in the forms directory and returns the URL to access that form.

    Accepts POST with job_details in request body to include job information on the form.
    
    Returns JSON response with:
    - success: boolean
    - message: string
    - job_requirement_id: string
    - form_url: string (URL to access the generated form)
    - form_path: string (local file path)

    When you visit the form_url, you'll see the HTML form where users can fill data.
    The form submits directly to the main application's API endpoint.
    """
    try:
        # Get job details from POST request body (if available)
        job_details = {}
        has_job_details = False
        
        if request.method == 'POST' and request.is_json:
            data = request.get_json()
            job_details = data.get('job_details', {})
            has_job_details = bool(job_details)
            
            logger.info(f"Received job details for form generation: {job_details}")
        
        # Sanitize the job_requirement_id for filename
        safe_filename = f"{job_requirement_id}.html"
        form_file_path = FORMS_DIR / safe_filename

        # Prepare template variables
        template_vars = {
            'job_requirement_id': job_requirement_id,
            'api_endpoint': MAIN_APP_API_ENDPOINT,
            'has_job_details': has_job_details,
            'job_title': job_details.get('title', 'Job Position'),
            'job_department': job_details.get('department', 'N/A'),
            'job_location': job_details.get('location', 'N/A'),
            'job_description': job_details.get('description', 'N/A'),
            'job_type': job_details.get('job_type', ''),
            'salary_range': job_details.get('salary_range'),
            'experience': job_details.get('experience'),
            'requirements': job_details.get('requirements', []),
            'benefits': job_details.get('benefits', [])
        }

        # Create the HTML content
        html_content = render_template_string(
            FORM_TEMPLATE,
            **template_vars
        )

        # Save the HTML file to the forms directory
        with open(form_file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        # Generate the URL to access the form
        form_url = f"http://{SERVICE_HOST}:{SERVICE_PORT}/forms/{job_requirement_id}.html"

        logger.info(f"Generated form for job requirement ID: {job_requirement_id}")
        logger.info(f"Form saved at: {form_file_path}")
        logger.info(f"Form URL: {form_url}")

        # Return JSON response with the form URL
        return jsonify({
            "success": True,
            "message": "Form generated successfully",
            "job_requirement_id": job_requirement_id,
            "form_url": form_url,
            "form_path": str(form_file_path)
        })

    except Exception as e:
        logger.error(f"Error generating form: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "message": f"Failed to generate application form: {str(e)}",
            "job_requirement_id": job_requirement_id,
            "error": str(e)
        }), 500


@app.route('/forms/<filename>')
def serve_form(filename):
    """
    Serve a previously generated HTML form file.
    """
    try:
        return send_from_directory(FORMS_DIR, filename)
    except Exception as e:
        logger.error(f"Error serving form: {str(e)}")
        return f"<h1>Error</h1><p>Form not found: {filename}</p>", 404


@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.
    """
    return {
        "status": "healthy",
        "service": "dynamic-form-service",
        "forms_directory": str(FORMS_DIR),
        "forms_count": len(list(FORMS_DIR.glob("*.html")))
    }


@app.route('/')
def index():
    """
    Root endpoint with information about the service.
    """
    forms = list(FORMS_DIR.glob("*.html"))
    forms_info = [{"filename": f.name, "job_id": f.stem} for f in forms]
    
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dynamic Form Service</title>
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
            }
            .badge-custom {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="service-title">🚀 Dynamic Form Service</h1>
            <p class="lead">Generate and serve job application forms dynamically</p>
            
            <div class="alert alert-info">
                <strong>Status:</strong> <span class="badge badge-custom text-white">Running</span>
            </div>
            
            <h3 class="mt-4">📋 How to Use</h3>
            <div class="code-block">
                <strong>Generate/Access a form:</strong><br>
                <code>GET http://localhost:8889/interview-management-service/api/v1/candidates/apply/{job_requirement_id}</code>
            </div>
            
            <h3 class="mt-4">📊 Generated Forms</h3>
            <p><strong>Total forms generated:</strong> {{ forms_count }}</p>
            
            {% if forms_info %}
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
                        {% for form in forms_info %}
                        <tr>
                            <td><code>{{ form.job_id }}</code></td>
                            <td>{{ form.filename }}</td>
                            <td>
                                <a href="/forms/{{ form.filename }}" class="btn btn-sm btn-primary" target="_blank">View Form</a>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% else %}
            <div class="alert alert-warning">
                No forms generated yet. Access the endpoint above to generate your first form!
            </div>
            {% endif %}
            
            <h3 class="mt-4">ℹ️ Service Information</h3>
            <ul>
                <li><strong>Port:</strong> 8888</li>
                <li><strong>Forms Directory:</strong> <code>{{ forms_directory }}</code></li>
                <li><strong>Main App API:</strong> <code>http://localhost:8888/interview-management-service/api/v1/candidates/apply</code></li>
                <li><strong>Health Check:</strong> <a href="/health" target="_blank">/health</a></li>
            </ul>
        </div>
    </body>
    </html>
    """
    
    return render_template_string(html, 
                                 forms_count=len(forms), 
                                 forms_info=forms_info,
                                 forms_directory=str(FORMS_DIR))


if __name__ == '__main__':
    logger.info("Starting Dynamic Form Service...")
    logger.info(f"Forms will be stored in: {FORMS_DIR}")
    logger.info(f"Service available at: http://{SERVICE_HOST}:{SERVICE_PORT}")
    logger.info(f"Main App API: {MAIN_APP_API_ENDPOINT}")
    
    app.run(
        host=SERVICE_HOST,
        port=SERVICE_PORT,
        debug=DEBUG_MODE
    )

