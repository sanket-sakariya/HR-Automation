"""
Configuration file for Dynamic Form Service
Modify these settings to customize the service behavior
"""

# Service Configuration
SERVICE_HOST = '0.0.0.0'  # Listen on all interfaces
SERVICE_PORT = 8889       # Port number (different from main app)
DEBUG_MODE = True         # Enable/disable debug mode

# Main Application API Configuration
MAIN_APP_BASE_URL = 'http://localhost:8888'
MAIN_APP_API_ENDPOINT = f'{MAIN_APP_BASE_URL}/interview-management-service/api/v1/candidates/apply'

# Directory Configuration
FORMS_DIRECTORY_NAME = 'forms'  # Name of the directory to store generated forms

# Form Styling (Bootstrap CDN)
BOOTSTRAP_CSS_CDN = 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css'
BOOTSTRAP_JS_CDN = 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js'

# Form Configuration
FORM_TITLE = 'Job Application Form'
COMPANY_NAME = 'Your Company Name'  # Optional: Add company name to forms

# File Upload Configuration
ALLOWED_RESUME_EXTENSIONS = ['.pdf']  # Client-side validation
MAX_FILE_SIZE_MB = 10  # Maximum file size (for reference, actual validation in main app)

# Form Field Configuration
REQUIRED_FIELDS = [
    'first_name',
    'last_name',
    'email',
    'resume'
]

OPTIONAL_FIELDS = [
    'phone',
    'linkedin_url',
    'portfolio_url',
    'skills',
    'current_location',
    'willing_to_relocate',
    'expected_salary',
    'notice_period'
]

# Logging Configuration
LOG_LEVEL = 'INFO'  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Success/Error Messages
SUCCESS_MESSAGE = 'Your application has been submitted successfully.'
ERROR_MESSAGE = 'Failed to submit application. Please try again.'
NETWORK_ERROR_MESSAGE = 'Network error. Please check your connection and try again.'

# Form Themes/Colors
PRIMARY_COLOR = '#667eea'
SECONDARY_COLOR = '#764ba2'
SUCCESS_COLOR = '#28a745'
ERROR_COLOR = '#dc3545'

# Feature Flags
ENABLE_FORM_VALIDATION = True
ENABLE_AJAX_SUBMISSION = True
ENABLE_FORM_CACHING = True
SHOW_JOB_DETAILS = False  # Future feature: Show job details in form

