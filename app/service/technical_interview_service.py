"""Technical Interview Service - Business logic for technical interview management."""

from __future__ import annotations
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.logger_config import log_central
from app.repository.technical_interview_repository import TechnicalInterviewRepository
from app.repository.candidate_repository import CandidateRepository
from app.repository.job_requirement_repository import JobRequirementRepository
from app.model.technical_interview_model import TechnicalInterviewModel


class TechnicalInterviewService:
    """Service for managing technical interviews."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.interview_repo = TechnicalInterviewRepository(db)
        self.candidate_repo = CandidateRepository(db)
        self.job_repo = JobRequirementRepository(db)

    async def validate_candidate_login(
        self, 
        email: str, 
        password: str, 
        job_requirement_id: UUID
    ) -> Dict[str, Any]:
        """
        Validate candidate credentials for technical interview.
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
        
        # Check if candidate has passed aptitude test (optional prerequisite)
        # if candidate.aptitude_test_result != "pass":
        #     return {
        #         "valid": False,
        #         "error": "Candidate must pass aptitude test before technical interview"
        #     }
        
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
        Create a new technical interview session.
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
                "error": "Technical interview already completed for this job",
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
        session_id = f"TI-{uuid4().hex[:12]}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
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
        technical_interview_id: UUID
    ) -> Optional[TechnicalInterviewModel]:
        """Mark interview as started."""
        return await self.interview_repo.start_interview(technical_interview_id)

    async def complete_interview(
        self, 
        technical_interview_id: UUID,
        completion_data: Dict[str, Any]
    ) -> Optional[TechnicalInterviewModel]:
        """
        Complete the interview with all results and scores.
        Also updates the candidate's technical_test fields.
        """
        interview = await self.interview_repo.get_by_id(technical_interview_id)
        if not interview:
            return None
        
        # Complete the interview
        updated_interview = await self.interview_repo.complete_interview(
            technical_interview_id, 
            completion_data
        )
        
        if updated_interview:
            # Update candidate's technical test status
            result = completion_data.get("result", "fail")
            await self.candidate_repo.update(
                updated_interview.candidate_id,
                {
                    "technical_test": True,
                    "technical_test_result": result
                }
            )
        
        return updated_interview

    async def get_interview_by_id(
        self, 
        technical_interview_id: UUID
    ) -> Optional[TechnicalInterviewModel]:
        """Get interview by ID."""
        return await self.interview_repo.get_by_id(technical_interview_id)

    async def get_interview_by_session(
        self, 
        session_id: str
    ) -> Optional[TechnicalInterviewModel]:
        """Get interview by session ID."""
        return await self.interview_repo.get_by_session_id(session_id)

    async def get_interviews_by_job(
        self, 
        job_requirement_id: UUID,
        status: Optional[str] = None
    ) -> List[TechnicalInterviewModel]:
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
        Select top N candidates based on technical interview scores.
        Updates their technical_test_result to 'pass' or 'fail'.
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
                "technical_knowledge_score": interview.technical_knowledge_score,
                "communication_score": interview.communication_score,
                "confidence_score": interview.confidence_score,
                "ai_recommendation": interview.ai_recommendation,
                "rank": idx + 1
            }
            
            if idx < top_n:
                # Update as passed
                await self.interview_repo.update_interview(
                    interview.technical_interview_id,
                    {"result": "pass"}
                )
                if candidate:
                    await self.candidate_repo.update(
                        candidate.candidate_id,
                        {"technical_test_result": "pass"}
                    )
                candidate_info["result"] = "pass"
                selected.append(candidate_info)
            else:
                # Update as failed
                await self.interview_repo.update_interview(
                    interview.technical_interview_id,
                    {"result": "fail"}
                )
                if candidate:
                    await self.candidate_repo.update(
                        candidate.candidate_id,
                        {"technical_test_result": "fail"}
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
        Generate a customized system instruction for the AI interviewer
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
        Generate a comprehensive master prompt for the AI interviewer
        based on job requirements, candidate profile, and resume.
        """
        title = job_details.get("title", "Technical Position")
        department = job_details.get("department", "Technology")
        description = job_details.get("description", "")
        requirements = job_details.get("requirements", [])
        experience = job_details.get("experience", {})
        
        # Extract skills from requirements
        skills = []
        for req in requirements:
            if isinstance(req, dict):
                skill = req.get("skill", "")
                if skill:
                    skills.append(skill)
        
        skills_str = ", ".join(skills[:10]) if skills else "general technical skills"
        
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
            resume_summary = resume_text[:2000] if len(resume_text) > 2000 else resume_text
            resume_section = f"""
CANDIDATE RESUME SUMMARY:
{resume_summary}
---
Use this resume information to:
- Ask relevant questions about their past projects
- Probe deeper into technologies they've mentioned
- Verify claims made in the resume
- Ask about specific experiences listed
"""
        
        system_instruction = f"""You are a Senior Technical Recruiter conducting a real-time voice interview for the position of "{title}" in the {department} department.

JOB CONTEXT:
- Position: {title}
- Department: {department}
- Required Experience: {exp_min}-{exp_max} years
- Key Skills Required: {skills_str}
- Job Description: {description[:500]}...

CANDIDATE PROFILE:
- Name: {candidate_name}
- Skills on Application: {candidate_skills_str}
{resume_section}

CRITICAL INTERVIEW TIMING:
- MINIMUM Interview Duration: 5 minutes
- MAXIMUM Interview Duration: 15 minutes
- You MUST conduct the interview for at least 5 minutes
- You MUST wrap up the interview by 15 minutes
- Pace your questions accordingly

CRITICAL SPEAKING GUIDELINES:
- Speak at a MODERATE, CLEAR pace - not too fast, not too slow
- Pronounce each word clearly and distinctly
- Pause briefly between sentences for better comprehension
- Avoid rushing through sentences - take your time
- Speak naturally but ensure every word is understandable

LANGUAGE BEHAVIOR:
- Start the interview in English with a warm greeting
- Address the candidate by their first name: {candidate_name.split()[0] if candidate_name and candidate_name != "the candidate" else "candidate"}
- If the candidate speaks in Hindi, seamlessly switch to Hindi
- If the candidate speaks in Gujarati, seamlessly switch to Gujarati
- You can mix languages naturally if the candidate does so
- Always match the language preference of the candidate

INTERVIEW STRUCTURE (Total: 5-15 minutes):

1. INTRODUCTION (1-2 mins):
   - Warm greeting using candidate's name
   - Brief overview of the interview process
   - Put the candidate at ease

2. BACKGROUND VERIFICATION (2-3 mins):
   - Ask about their experience mentioned in resume
   - Current/previous role responsibilities
   - Why they're interested in this position

3. TECHNICAL ASSESSMENT (5-8 mins):
   - Ask questions specific to: {skills_str}
   - Start with easier questions, gradually increase difficulty
   - If resume available, ask about specific projects/technologies mentioned
   - Probe deeper based on their responses
   - Ask follow-up questions to assess depth of knowledge

4. PROBLEM SOLVING (2-3 mins):
   - Present a relevant scenario or problem
   - Assess their analytical thinking
   - Evaluate their approach to problem-solving

5. CLOSING (1 min):
   - Ask if they have questions
   - Thank them for their time
   - Mention next steps

EVALUATION CRITERIA (Assess throughout):
- Technical Knowledge: Understanding of core concepts
- Problem Solving: Analytical and logical thinking
- Communication: Clarity, articulation, language proficiency
- Confidence: How confidently they present themselves
- Enthusiasm: Interest in the role and company
- Relevance: How well their answers relate to questions

INTERVIEWER GUIDELINES:
- Ask ONE question at a time and wait for complete response
- Be encouraging and supportive
- If answer is unclear, politely ask for clarification
- Keep responses concise - avoid long monologues
- Acknowledge good answers positively
- Note any areas where candidate struggles
- Personalize questions based on candidate's resume if available

TIME MANAGEMENT:
- Keep track of time mentally
- If interview is too short (< 5 mins), ask more questions
- If approaching 15 mins, start wrapping up
- End professionally when time is up

Remember: This is a VOICE conversation. Keep responses concise and natural. No markdown, bullet points, or text formatting. Sound human, not robotic. SPEAK CLEARLY AND AT A COMFORTABLE PACE.

At the end, mentally note your assessment but do not share scores with the candidate. Simply thank them and close professionally."""

        return system_instruction
