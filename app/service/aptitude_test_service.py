"""Aptitude Test Service - Business logic for test management."""

from __future__ import annotations
from typing import Optional, Dict, Any, List
from uuid import UUID
import time
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.logger_config import log_central
from app.repository.aptitude_test_repository import AptitudeTestRepository
from app.repository.job_requirement_repository import JobRequirementRepository
from app.service.email_otp_service import EmailOTPService
from app.schema.aptitude_test_schema import (
    AptitudeTestRead,
    AptitudeQuestionRead,
    TestAttemptResult
)
from app.exception.job_requirement_exception import JobRequirementNotFoundException

# Import Gemini AI
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class AptitudeTestService:
    """Service for managing aptitude tests."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.test_repo = AptitudeTestRepository(db)
        self.job_repo = JobRequirementRepository(db)
        self.email_service = EmailOTPService()
        
        # Initialize Gemini AI with JSON mode
        if GEMINI_AVAILABLE:
            genai.configure(api_key="AIzaSyDHNd6W382fBzwf_HbPxf70sxG13XE9xgA")
            
            # Configure generation parameters for clean JSON output
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,
                "response_mime_type": "application/json",  # Force JSON output
            }
            
            self.model = genai.GenerativeModel(
                'gemini-2.5-flash',
                generation_config=generation_config
            )
        else:
            self.model = None

    @staticmethod
    def _clean_json_string(text: str) -> str:
        """Clean invalid control characters from JSON string."""
        import re
        # Remove control characters except newlines, tabs, and carriage returns
        cleaned = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
        # Replace unescaped newlines in strings with spaces
        cleaned = cleaned.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        return cleaned

    def _generate_test_prompt(self, job_details: dict) -> str:
        """Generate AI prompt for test creation."""
        job_title = job_details.get('title', 'Position')
        department = job_details.get('department', 'General')
        description = job_details.get('description', '')
        requirements = job_details.get('requirements', [])
        
        # Extract skills
        skills = []
        for req in requirements:
            if isinstance(req, dict):
                skills.append(req.get('skill', ''))
        
        prompt = f"""
You are an EXPERT APTITUDE TEST GENERATOR. Create a comprehensive test for "{job_title}" position.

JOB DETAILS:
Position: {job_title}
Department: {department}
Description: {description}
Required Skills: {', '.join(skills[:10])}

Generate EXACTLY 30 questions with this distribution:
- 12 Simple questions (40%)
- 12 Medium questions (40%)
- 6 Hard questions (20%)

Return ONLY valid JSON in this format:
{{
  "test_metadata": {{
    "test_title": "{job_title} - Aptitude Test",
    "total_questions": 30,
    "passing_score": 60
  }},
  "questions": [
    {{
      "question_number": 1,
      "difficulty": "simple",
      "category": "core_logic",
      "question_text": "Question here",
      "options": {{"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"}},
      "correct_answer": "A",
      "explanation": "Why A is correct",
      "time_allocated_seconds": 60,
      "tags": ["tag1", "tag2"]
    }}
  ]
}}

CRITICAL RULES:
- Exactly 30 questions
- All MCQ with 4 options (A, B, C, D)
- Questions relevant to {job_title}
- Return ONLY JSON, no markdown
- NO line breaks or newline characters (\\n) inside question text or options
- NO special characters like tabs (\\t) or control characters
- Use simple plain text only
- Keep all text on single lines
"""
        return prompt

    async def generate_and_store_test(self, job_requirement_id: UUID) -> Dict[str, Any]:
        """Generate test using AI and store in database."""
        try:
            # Check if test already exists
            existing_test = await self.test_repo.get_test_by_job_id(job_requirement_id)
            if existing_test:
                return {
                    "aptitude_test_id": existing_test.aptitude_test_id,
                    "already_exists": True,
                    "message": "Test already exists for this job"
                }

            # Get job details
            job_requirement = await self.job_repo.get_by_id(job_requirement_id)
            if not job_requirement:
                raise JobRequirementNotFoundException(job_requirement_id)

            job_details = {
                'title': job_requirement.title,
                'department': job_requirement.department,
                'description': job_requirement.description,
                'requirements': job_requirement.requirements
            }

            log_central(f"Generating test for job: {job_details['title']}", level="info")

            # Generate test using AI
            if not self.model:
                raise Exception("AI model not available")

            prompt = self._generate_test_prompt(job_details)
            
            start_time = time.time()
            response = self.model.generate_content(prompt)
            processing_time = time.time() - start_time

            # Parse response
            import json
            response_text = response.text.strip()
            
            # Remove markdown
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            # Clean control characters
            response_text = self._clean_json_string(response_text.strip())
            
            # Log for debugging
            log_central(f"AI Response (first 500 chars): {response_text[:500]}", level="info")
            
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

            # Create test in database
            test_metadata = test_data.get('test_metadata', {})
            test_record = await self.test_repo.create_test({
                'job_requirement_id': job_requirement_id,
                'test_title': test_metadata.get('test_title', f"{job_details['title']} - Aptitude Test"),
                'total_questions': 30,
                'total_time_minutes': 45,
                'passing_score_percentage': test_metadata.get('passing_score', 60),
                'test_metadata': test_metadata,
                'proctoring_settings': {
                    'tab_switch_detection': True,
                    'max_tab_switches_allowed': 3,
                    'copy_paste_detection': True,
                    'fullscreen_mode': True
                },
                'is_active': True
            })

            # Store questions
            questions_data = []
            for q in test_data.get('questions', []):
                questions_data.append({
                    'job_requirement_id': job_requirement_id,
                    'aptitude_test_id': test_record.aptitude_test_id,
                    'question_number': q['question_number'],
                    'difficulty': q['difficulty'],
                    'category': q['category'],
                    'question_text': q['question_text'],
                    'options': q['options'],
                    'correct_answer': q['correct_answer'],
                    'explanation': q.get('explanation'),
                    'time_allocated_seconds': q.get('time_allocated_seconds', 90),
                    'tags': q.get('tags', [])
                })

            await self.test_repo.bulk_create_questions(questions_data)

            log_central(
                f"Test created successfully: {test_record.aptitude_test_id} with {len(questions_data)} questions",
                level="info"
            )

            return {
                "aptitude_test_id": test_record.aptitude_test_id,
                "test_title": test_record.test_title,
                "questions_generated": len(questions_data),
                "already_exists": False
            }

        except Exception as e:
            log_central(f"Error generating test: {str(e)}", level="error")
            raise

    async def start_test_attempt(
        self,
        job_requirement_id: UUID,
        aptitude_test_id: UUID,
        candidate_email: str,
        candidate_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Start a new test attempt and send OTP."""
        try:
            # Verify test exists
            test = await self.test_repo.get_test_by_id(aptitude_test_id)
            if not test or test.job_requirement_id != job_requirement_id:
                raise Exception("Test not found or doesn't match job requirement")

            # Generate OTP
            otp_code = self.email_service.generate_otp()

            # Create attempt record
            attempt = await self.test_repo.create_attempt({
                'aptitude_test_id': aptitude_test_id,
                'job_requirement_id': job_requirement_id,
                'candidate_email': candidate_email,
                'candidate_name': candidate_name,
                'otp_code': otp_code,
                'otp_verified': False,
                'status': 'pending'
            })

            # Send OTP email
            email_sent = self.email_service.send_otp_email(
                recipient_email=candidate_email,
                otp_code=otp_code,
                test_title=test.test_title
            )

            if not email_sent:
                log_central(f"Failed to send OTP email to {candidate_email}", level="warning")

            return {
                "attempt_id": attempt.attempt_id,
                "otp_sent": email_sent,
                "message": "OTP sent to your email" if email_sent else "OTP generated (check logs)"
            }

        except Exception as e:
            log_central(f"Error starting test attempt: {str(e)}", level="error")
            raise

    async def verify_otp_and_get_test(
        self,
        attempt_id: UUID,
        otp_code: str
    ) -> Dict[str, Any]:
        """Verify OTP and return test questions."""
        try:
            # Get attempt
            attempt = await self.test_repo.get_attempt_by_id(attempt_id)
            if not attempt:
                raise Exception("Test attempt not found")

            # Verify OTP
            if not self.email_service.verify_otp(otp_code, attempt.otp_code):
                raise Exception("Invalid OTP code")

            # Check if already verified
            if attempt.otp_verified:
                log_central(f"OTP already verified for attempt {attempt_id}", level="info")

            # Update attempt as verified
            await self.test_repo.update_attempt(attempt_id, {
                'otp_verified': True,
                'otp_verified_at': datetime.now().isoformat(),
                'status': 'in_progress',
                'started_at': datetime.now().isoformat()
            })

            # Get test and questions (without answers)
            test = await self.test_repo.get_test_by_id(attempt.aptitude_test_id)
            questions = await self.test_repo.get_questions_by_test_id(attempt.aptitude_test_id)

            # Format questions (remove correct answers)
            questions_public = []
            for q in questions:
                questions_public.append({
                    'question_id': str(q.question_id),
                    'question_number': q.question_number,
                    'difficulty': q.difficulty,
                    'category': q.category,
                    'question_text': q.question_text,
                    'options': q.options,
                    'time_allocated_seconds': q.time_allocated_seconds,
                    'tags': q.tags
                })

            return {
                "test": {
                    "aptitude_test_id": str(test.aptitude_test_id),
                    "test_title": test.test_title,
                    "total_questions": test.total_questions,
                    "total_time_minutes": test.total_time_minutes,
                    "passing_score_percentage": test.passing_score_percentage,
                    "proctoring_settings": test.proctoring_settings,
                    "questions": questions_public
                },
                "attempt_id": str(attempt_id),
                "candidate_name": attempt.candidate_name
            }

        except Exception as e:
            log_central(f"Error verifying OTP: {str(e)}", level="error")
            raise

    async def submit_test_answers(
        self,
        attempt_id: UUID,
        answers: Dict[int, str],
        time_taken_seconds: int,
        tab_switches: int = 0
    ) -> Dict[str, Any]:
        """Submit test answers and calculate score."""
        try:
            # Get attempt
            attempt = await self.test_repo.get_attempt_by_id(attempt_id)
            if not attempt:
                raise Exception("Test attempt not found")

            if not attempt.otp_verified:
                raise Exception("Test not verified")

            if attempt.status == 'completed':
                raise Exception("Test already submitted")

            # Get questions with correct answers
            questions = await self.test_repo.get_questions_by_test_id(attempt.aptitude_test_id)

            # Calculate score
            correct_count = 0
            for q in questions:
                q_index = q.question_number - 1  # Convert to 0-based index
                if str(q_index) in answers and answers[str(q_index)] == q.correct_answer:
                    correct_count += 1

            total_questions = len(questions)
            score = (correct_count / total_questions * 100) if total_questions > 0 else 0
            
            # Get test to check passing score
            test = await self.test_repo.get_test_by_id(attempt.aptitude_test_id)
            passed = score >= test.passing_score_percentage

            # Update attempt
            await self.test_repo.update_attempt(attempt_id, {
                'answers': answers,
                'score': round(score, 2),
                'correct_answers_count': correct_count,
                'total_questions_attempted': len(answers),
                'passed': passed,
                'time_taken_seconds': time_taken_seconds,
                'tab_switches': tab_switches,
                'status': 'completed',
                'submitted_at': datetime.now().isoformat()
            })

            log_central(
                f"Test submitted: attempt_id={attempt_id}, score={score:.2f}%, passed={passed}",
                level="info"
            )

            return {
                "attempt_id": attempt_id,
                "candidate_email": attempt.candidate_email,
                "candidate_name": attempt.candidate_name,
                "score": round(score, 2),
                "correct_answers_count": correct_count,
                "total_questions_attempted": len(answers),
                "total_questions": total_questions,
                "passed": passed,
                "time_taken_seconds": time_taken_seconds,
                "submitted_at": datetime.now().isoformat()
            }

        except Exception as e:
            log_central(f"Error submitting test: {str(e)}", level="error")
            raise

