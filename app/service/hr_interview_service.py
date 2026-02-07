"""HR Interview Service - Business logic for HR interview management."""

from __future__ import annotations
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.logger_config import log_central
from app.repository.hr_interview_repository import HRInterviewRepository
from app.repository.candidate_repository import CandidateRepository
from app.repository.job_requirement_repository import JobRequirementRepository
from app.model.hr_interview_model import HRInterviewModel


class HRInterviewService:
    """Service for managing HR interviews."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.interview_repo = HRInterviewRepository(db)
        self.candidate_repo = CandidateRepository(db)
        self.job_repo = JobRequirementRepository(db)

    async def validate_candidate_login(
        self, 
        email: str, 
        password: str, 
        job_requirement_id: UUID
    ) -> Dict[str, Any]:
        """
        Validate candidate credentials for HR interview.
        Same credentials as aptitude test.
        """
        # Get candidate by email and job requirement
        candidate = await self.candidate_repo.get_by_email_and_job_requirement(
            email, str(job_requirement_id)
        )
        
        if not candidate:
            return {
                "valid": False,
                "error": "Candidate not found for this job requirement"
            }
        
        # Verify password
        if candidate.password != password:
            return {
                "valid": False,
                "error": "Invalid password"
            }
        
        return {
            "valid": True,
            "candidate": candidate
        }

    async def create_interview_session(
        self, 
        candidate_id: UUID, 
        job_requirement_id: UUID
    ) -> Dict[str, Any]:
        """
        Create a new HR interview session.
        Returns interview details and WebSocket URL for the interview.
        """
        # Check if interview already exists
        existing = await self.interview_repo.get_pending_interview(
            candidate_id, job_requirement_id
        )
        
        if existing:
            # Return existing pending interview
            job = await self.job_repo.get_by_id(job_requirement_id)
            candidate = await self.candidate_repo.get_by_id(candidate_id)
            
            return {
                "interview": existing,
                "job_details": self._format_job_details(job),
                "candidate_info": self._format_candidate_info(candidate),
                "is_existing": True
            }
        
        # Check if already completed
        completed = await self.interview_repo.check_interview_exists(
            candidate_id, job_requirement_id
        )
        if completed:
            return {
                "error": "HR interview already completed for this job",
                "already_completed": True
            }
        
        # Get job details for interview context
        job = await self.job_repo.get_by_id(job_requirement_id)
        if not job:
            return {"error": "Job requirement not found"}
        
        # Get candidate details
        candidate = await self.candidate_repo.get_by_id(candidate_id)
        if not candidate:
            return {"error": "Candidate not found"}
        
        # Generate unique session ID
        session_id = f"HR-{uuid4().hex[:12]}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Create interview record
        interview_data = {
            "job_requirement_id": job_requirement_id,
            "candidate_id": candidate_id,
            "interview_session_id": session_id,
            "interview_status": "pending",
            "ai_model_used": "gemini-2.5-flash-native-audio-preview-12-2025",
            "created_at": datetime.now(timezone.utc),
            "created_by": candidate_id,  # Candidate creates their own interview session
            "is_active": True,
            "status": "active"
        }
        
        interview = await self.interview_repo.create_interview(interview_data)
        
        return {
            "interview": interview,
            "job_details": self._format_job_details(job),
            "candidate_info": self._format_candidate_info(candidate),
            "is_existing": False
        }

    def _format_job_details(self, job) -> Dict[str, Any]:
        """Format job details for interview context."""
        if not job:
            return {}
        
        return {
            "job_requirement_id": str(job.job_requirement_id),
            "title": job.title,
            "department": job.department,
            "description": job.description,
            "requirements": job.requirements,
            "experience": job.experience,
            "location": job.location,
            "job_type": job.job_type
        }

    def _format_candidate_info(self, candidate) -> Dict[str, Any]:
        """Format candidate info."""
        if not candidate:
            return {}
        
        return {
            "candidate_id": str(candidate.candidate_id),
            "name": f"{candidate.first_name} {candidate.last_name}",
            "email": candidate.email,
            "skills": candidate.skills
        }

    async def start_interview(
        self, 
        hr_interview_id: UUID
    ) -> Optional[HRInterviewModel]:
        """Mark interview as started."""
        return await self.interview_repo.start_interview(hr_interview_id)

    async def complete_interview(
        self, 
        hr_interview_id: UUID,
        completion_data: Dict[str, Any]
    ) -> Optional[HRInterviewModel]:
        """
        Complete the interview with all results and scores.
        Also updates the candidate's hr_interview fields.
        """
        interview = await self.interview_repo.get_by_id(hr_interview_id)
        if not interview:
            return None
        
        # Complete the interview
        updated_interview = await self.interview_repo.complete_interview(
            hr_interview_id, 
            completion_data
        )
        
        if updated_interview:
            # Update candidate's HR interview status
            result = completion_data.get("result", "fail")
            await self.candidate_repo.update(
                updated_interview.candidate_id,
                {
                    "hr_test": True,
                    "hr_test_result": result
                }
            )
        
        return updated_interview

    async def get_interview_by_id(
        self, 
        hr_interview_id: UUID
    ) -> Optional[HRInterviewModel]:
        """Get interview by ID."""
        return await self.interview_repo.get_by_id(hr_interview_id)

    async def get_interview_by_session(
        self, 
        session_id: str
    ) -> Optional[HRInterviewModel]:
        """Get interview by session ID."""
        return await self.interview_repo.get_by_session_id(session_id)

    async def get_interviews_by_job(
        self, 
        job_requirement_id: UUID,
        status: Optional[str] = None
    ) -> List[HRInterviewModel]:
        """Get all interviews for a job requirement."""
        return await self.interview_repo.get_interviews_by_job(
            job_requirement_id, status
        )

    async def get_interview_statistics(
        self, 
        job_requirement_id: UUID
    ) -> Dict[str, Any]:
        """Get interview statistics for a job requirement."""
        return await self.interview_repo.get_interview_statistics(job_requirement_id)

    async def select_top_candidates(
        self, 
        job_requirement_id: UUID, 
        top_n: int
    ) -> Dict[str, Any]:
        """
        Select top N candidates based on HR interview scores.
        Updates their hr_interview_result to 'pass' or 'fail'.
        """
        # Get all completed interviews sorted by score
        interviews = await self.interview_repo.get_completed_interviews_by_job_sorted_by_score(
            job_requirement_id
        )
        
        if not interviews:
            return {
                "total_interviews": 0,
                "selected_count": 0,
                "rejected_count": 0,
                "selected_candidates": [],
                "rejected_candidates": []
            }
        
        selected = []
        rejected = []
        
        for idx, interview in enumerate(interviews):
            candidate = await self.candidate_repo.get_by_id(interview.candidate_id)
            candidate_info = {
                "candidate_id": str(interview.candidate_id),
                "candidate_email": candidate.email if candidate else "N/A",
                "candidate_name": f"{candidate.first_name} {candidate.last_name}" if candidate else "N/A",
                "overall_score": interview.overall_score,
                "communication_score": interview.communication_score,
                "confidence_score": interview.confidence_score,
                "cultural_fit_score": interview.cultural_fit_score,
                "teamwork_score": interview.teamwork_score,
                "ai_recommendation": interview.ai_recommendation,
                "rank": idx + 1
            }
            
            if idx < top_n:
                # Update as passed
                await self.interview_repo.update_interview(
                    interview.hr_interview_id,
                    {"result": "pass"}
                )
                if candidate:
                    await self.candidate_repo.update(
                        candidate.candidate_id,
                        {"hr_test_result": "pass"}
                    )
                candidate_info["result"] = "pass"
                selected.append(candidate_info)
            else:
                # Update as failed
                await self.interview_repo.update_interview(
                    interview.hr_interview_id,
                    {"result": "fail"}
                )
                if candidate:
                    await self.candidate_repo.update(
                        candidate.candidate_id,
                        {"hr_test_result": "fail"}
                    )
                candidate_info["result"] = "fail"
                rejected.append(candidate_info)
        
        return {
            "total_interviews": len(interviews),
            "selected_count": len(selected),
            "rejected_count": len(rejected),
            "selected_candidates": selected,
            "rejected_candidates": rejected
        }

    def generate_system_instruction(self, job_details: Dict[str, Any]) -> str:
        """
        Generate a customized system instruction for the AI HR interviewer
        based on the job requirements (backward compatibility).
        """
        return self.generate_master_prompt(job_details, {}, None)

    def generate_master_prompt(
        self, 
        job_details: Dict[str, Any], 
        candidate_info: Dict[str, Any],
        resume_text: Optional[str] = None
    ) -> str:
        """
        Generate a comprehensive master prompt for the AI HR interviewer
        based on job requirements, candidate profile, and resume.
        """
        title = job_details.get("title", "Position")
        department = job_details.get("department", "")
        description = job_details.get("description", "")
        requirements = job_details.get("requirements", [])
        experience = job_details.get("experience", {})
        
        exp_min = experience.get("minYears", 0) if experience else 0
        exp_max = experience.get("maxYears", 5) if experience else 5
        
        # Candidate info section
        candidate_name = candidate_info.get("name", "the candidate")
        candidate_skills = candidate_info.get("skills", [])
        candidate_skills_str = ", ".join(candidate_skills[:10]) if candidate_skills else "Not specified"
        
        # Resume summary section
        resume_section = ""
        if resume_text:
            # Truncate resume text to prevent token overflow
            resume_summary = resume_text[:3000] if len(resume_text) > 3000 else resume_text
            resume_section = f"""
CANDIDATE RESUME:
{resume_summary}
---
"""
        
        system_instruction = f"""You are "Adhira", a Senior HR Manager conducting a comprehensive real-time voice HR interview for the position of "{title}" in the {department} department.

=== JOB CONTEXT ===
Position: {title}
Department: {department}
Required Experience: {exp_min}-{exp_max} years
Job Description: {description[:800]}

=== CANDIDATE PROFILE ===
Name: {candidate_name}
Skills Listed: {candidate_skills_str}
{resume_section}

=== CRITICAL RULES - YOU MUST FOLLOW ===

1. INTERVIEW FOCUS:
   - This is an HR/Behavioral interview, NOT a technical interview
   - Focus on: Communication, Attitude, Cultural Fit, Soft Skills, Career Goals
   - Ask behavioral questions using STAR method (Situation, Task, Action, Result)
   - Assess: Teamwork, Leadership, Problem-solving, Adaptability, Professionalism

2. INTERVIEW DURATION:
   - MINIMUM: 5 minutes (ask at least 8-10 questions)
   - MAXIMUM: 12 minutes (can ask up to 15-20 questions)
   - Keep conversations engaging but focused
   - NEVER end before 5 minutes regardless of answer quality

3. MULTILINGUAL SUPPORT (NO LANGUAGE BARRIER):
   - Start in English
   - If candidate speaks Hindi → switch to Hindi immediately
   - If candidate speaks Gujarati → switch to Gujarati immediately
   - If candidate mixes languages → you can mix too (Hinglish is fine)
   - NEVER ask candidate to speak in a specific language
   - Understand and respond in whatever language they use

4. ANSWER VERIFICATION:
   - ALWAYS listen to candidate's COMPLETE answer before responding
   - If unclear audio → say: "I couldn't understand that clearly. Could you please repeat?"
   - If candidate gives IRRELEVANT answer → say: "That doesn't seem to answer my question. Let me rephrase..."
   - If candidate stays SILENT → say: "Are you still there? Would you like me to repeat the question?"
   - If candidate says "I don't know" → acknowledge and move on

5. OFF-TOPIC QUESTIONS - STRICT RULES:
   - If candidate asks questions OUTSIDE interview context
   - RESPOND: "I appreciate your curiosity, but let's stay focused on the interview. Here's my next question..."
   - NEVER answer off-topic questions
   - NEVER engage in casual conversation outside interview scope

=== MANDATORY QUESTION CATEGORIES ===

CATEGORY A - INTRODUCTION & BACKGROUND (2-3 questions):
- Tell me about yourself
- Walk me through your career journey
- What motivated you to apply for this position?

CATEGORY B - BEHAVIORAL QUESTIONS (4-5 questions) - USE STAR METHOD:
- "Tell me about a time when you worked in a team to achieve a goal"
- "Describe a situation where you faced a conflict with a colleague"
- "Give an example of when you had to meet a tight deadline"
- "Tell me about a time you received constructive criticism"
- "Describe a challenging situation and how you handled it"

CATEGORY C - SOFT SKILLS ASSESSMENT (3-4 questions):
- How do you prioritize tasks when you have multiple deadlines?
- How do you handle stress or pressure at work?
- What's your approach to learning new things?
- How do you handle disagreements with your manager?

CATEGORY D - CULTURAL FIT & VALUES (2-3 questions):
- What kind of work environment do you thrive in?
- What are your long-term career goals?
- Why do you want to leave your current position (if applicable)?
- What do you value most in a workplace?

CATEGORY E - SITUATIONAL QUESTIONS (2-3 questions):
- What would you do if you were assigned a task you've never done before?
- How would you handle a situation where a team member isn't contributing?
- If you made a mistake at work, how would you handle it?

=== SPEAKING GUIDELINES ===
- Speak CLEARLY and at MODERATE pace
- Pause between sentences
- One question at a time
- Wait for complete answer before next question
- Acknowledge answers briefly ("Thank you", "Interesting", "I see")
- Be warm and encouraging - this is HR, not interrogation

=== INTERVIEW FLOW ===

PHASE 1 - WARM INTRODUCTION (1-2 mins):
"Hello {candidate_name.split()[0] if candidate_name and candidate_name != "the candidate" else "there"}! I'm Adhira, the HR Manager here. Welcome to the HR round of your interview for the {title} position. 
Before we begin, I want you to know that this is a conversational interview - there are no right or wrong answers. I want to understand you better as a person.
Let's start with a simple question - can you tell me a little about yourself and your journey so far?"

PHASE 2 - CAREER & MOTIVATION (2-3 mins):
- Career progression questions
- Motivation for this role
- Understanding of the position

PHASE 3 - BEHAVIORAL ASSESSMENT (3-4 mins):
- Use STAR method questions
- Probe for specific examples
- Listen for concrete situations

PHASE 4 - SOFT SKILLS & PERSONALITY (2-3 mins):
- Team collaboration style
- Conflict resolution approach
- Work ethic and values

PHASE 5 - CULTURAL FIT & FUTURE (2 mins):
- Career aspirations
- Work environment preferences
- Alignment with company values

PHASE 6 - CANDIDATE QUESTIONS & CLOSING (1 min):
- "Do you have any questions about the role or our company?"
- Thank them professionally
- "Thank you for speaking with me today. We'll be in touch with the next steps."

=== RESPONSE TRACKING ===
Mentally track after each answer:
- Did they use specific examples? (STAR method)
- Do they show self-awareness?
- Are they positive and professional?
- Do they seem genuine and authentic?
- Would they fit the company culture?

=== EXAMPLE HR QUESTIONS ===

Communication:
- "How do you ensure clear communication in a remote/hybrid setup?"
- "Tell me about a presentation you gave and how it went"

Teamwork:
- "Describe your ideal team environment"
- "How do you contribute to team success?"

Leadership:
- "Have you ever had to lead a project or team?"
- "How do you motivate others?"

Problem-solving:
- "Walk me through how you approach a new problem"
- "Tell me about a creative solution you came up with"

Adaptability:
- "How do you handle changes in priorities?"
- "Tell me about a time you had to learn something quickly"

=== IMPORTANT REMINDERS ===
- This is VOICE conversation - no markdown, no bullets, speak naturally
- Keep your responses SHORT (1-2 sentences max unless explaining something)
- Sound warm, friendly, and professional - you're representing the company
- Be encouraging and create a comfortable atmosphere
- NEVER reveal scores or evaluation to candidate
- Ask follow-up questions when answers are vague

=== INTERVIEW CLOSURE (VERY IMPORTANT) ===
When you have completed the interview (after asking sufficient questions, typically 10-15 questions or 8-12 minutes):
1. Thank the candidate warmly for their time
2. Ask if they have any questions for you
3. **CRITICAL**: Say clearly "Thank you for this wonderful conversation, {candidate_name.split()[0] if candidate_name else 'candidate'}. It was great getting to know you. Please click the 'End Session' button on your screen to complete the interview. We'll be in touch with the next steps soon. All the best!"
4. Do NOT continue asking questions after this closing statement

BEGIN THE INTERVIEW NOW."""

        return system_instruction
