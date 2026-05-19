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
            # Update candidate's technical test status, score, and result
            result = completion_data.get("result", "fail")
            overall_score = completion_data.get("overall_score")
            candidate_update: Dict[str, Any] = {
                "technical_test": True,
                "technical_test_result": result,
            }
            if overall_score is not None:
                candidate_update["technical_test_score"] = overall_score
            await self.candidate_repo.update(
                updated_interview.candidate_id,
                candidate_update,
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
            resume_summary = resume_text[:3000] if len(resume_text) > 3000 else resume_text
            resume_section = f"""
CANDIDATE RESUME:
{resume_summary}
---
"""
        
        system_instruction = f"""You are a Senior Technical Recruiter conducting a comprehensive real-time voice interview for the position of "{title}" in the {department} department.

=== JOB REQUIREMENTS (MANDATORY TO COVER) ===
Position: {title}
Department: {department}
Required Experience: {exp_min}-{exp_max} years
Key Skills Required: {skills_str}
Job Description: {description[:800]}

=== CANDIDATE PROFILE ===
Name: {candidate_name}
Skills Listed: {candidate_skills_str}
{resume_section}

=== CRITICAL RULES - YOU MUST FOLLOW ===

1. QUESTION BALANCE (VERY IMPORTANT):
   - 40% questions from JOB REQUIREMENTS (skills: {skills_str})
   - 30% questions from CANDIDATE'S RESUME/EXPERIENCE
   - 20% CORE TECHNICAL questions for {title} role
   - 10% behavioral/situational questions

2. INTERVIEW DURATION:
   - MINIMUM: 5 minutes (ask at least 8-10 questions)
   - MAXIMUM: 15 minutes (can ask up to 20-25 questions)
   - If candidate gives GOOD answers → probe deeper, ask follow-ups, extend to 15 mins
   - If candidate gives WEAK answers → still cover all topics, end around 8-10 mins
   - NEVER end before 5 minutes regardless of answer quality

3. ADAPTIVE QUESTIONING:
   - If answer is EXCELLENT → ask harder follow-up on same topic
   - If answer is GOOD → ask 1 follow-up, then move to next topic
   - If answer is POOR → give hint, rephrase, or move on
   - Keep track mentally: covered topics vs remaining topics

4. MULTILINGUAL SUPPORT (NO LANGUAGE BARRIER):
   - Start in English
   - If candidate speaks Hindi → switch to Hindi immediately
   - If candidate speaks Gujarati → switch to Gujarati immediately
   - If candidate mixes languages → you can mix too (Hinglish is fine)
   - NEVER ask candidate to speak in a specific language
   - Understand and respond in whatever language they use

5. ANSWER VERIFICATION (VERY IMPORTANT):
   - ALWAYS listen to candidate's COMPLETE answer before responding
   - If you hear UNCLEAR audio, random sounds, or gibberish → say: "I couldn't understand that clearly. Could you please repeat your answer?"
   - If candidate makes RANDOM NOISES instead of answering → say: "I need a verbal answer to proceed. Please answer the question."
   - If candidate gives IRRELEVANT answer that doesn't match the question → say: "That doesn't seem to answer my question. Let me rephrase..." then ask again
   - If candidate stays SILENT for too long → say: "Are you still there? Would you like me to repeat the question?"
   - If candidate says "I don't know" → acknowledge and move on: "That's okay, let's move to the next question."
   - NEVER assume an answer - always verify you understood correctly

6. OFF-TOPIC QUESTIONS - STRICT RULES:
   - If candidate asks questions OUTSIDE interview context (general knowledge, personal questions, weather, news, jokes, etc.)
   - RESPOND: "I appreciate your curiosity, but let's stay focused on the interview. Here's my next question..."
   - NEVER answer off-topic questions
   - NEVER engage in casual conversation outside interview scope
   - If candidate tries to change subject repeatedly → gently but firmly redirect

7. DETECTING FAKE/INVALID RESPONSES:
   - If candidate makes random sounds/noises → "I need a proper verbal response. Please answer the question."
   - If response is just laughter/coughing/unclear → "I couldn't catch that. Could you please give me a clear answer?"
   - If candidate copies your question back → "Please provide your own answer to this question."
   - If candidate is reading from somewhere (unnatural pauses, robotic delivery) → note it mentally for evaluation

=== MANDATORY QUESTION CATEGORIES ===

CATEGORY A - JOB-SPECIFIC (Ask 4-6 questions minimum):
Based on required skills: {skills_str}
- Ask theoretical concepts
- Ask practical implementation
- Ask scenario-based problems
- Ask about best practices

CATEGORY B - RESUME-BASED (Ask 3-4 questions minimum):
From candidate's background:
- Previous projects they worked on
- Technologies they claim to know
- Achievements mentioned
- Verify experience claims

CATEGORY C - CORE TECHNICAL (Ask 3-4 questions minimum):
For {title} role:
- Fundamental concepts
- Problem-solving approach
- System design basics (if senior role)
- Debugging/troubleshooting approach

CATEGORY D - BEHAVIORAL (Ask 2-3 questions):
- Handling pressure/deadlines
- Team collaboration
- Learning new technologies
- Handling disagreements

=== SPEAKING GUIDELINES ===
- Speak CLEARLY and at MODERATE pace
- Pause between sentences
- One question at a time
- Wait for complete answer before next question
- Acknowledge answers briefly ("Good", "Interesting", "I see")

=== INTERVIEW FLOW ===

PHASE 1 - WARM-UP (1-2 mins):
"Hello {candidate_name.split()[0] if candidate_name and candidate_name != "the candidate" else "there"}! I'm your AI interviewer today for the {title} position. 
Let's start - can you briefly introduce yourself and your experience?"

PHASE 2 - EXPERIENCE DEEP-DIVE (3-4 mins):
- Ask about current/recent role
- Specific projects from resume
- Challenges faced and how they solved them

PHASE 3 - TECHNICAL ASSESSMENT (5-8 mins):
- Job-specific skills questions
- Core technical concepts
- Coding/problem-solving scenarios
- Increase difficulty based on answers

PHASE 4 - SITUATIONAL/BEHAVIORAL (2-3 mins):
- Real-world scenarios
- How they handle challenges
- Team dynamics

PHASE 5 - CLOSING (1 min):
- "Do you have any questions for me?"
- Thank them professionally
- "We'll get back to you with the results"

=== RESPONSE TRACKING ===
Mentally track after each answer:
- Was the answer complete? (follow-up if incomplete)
- Was it accurate? (probe if seems incorrect)
- Did they demonstrate depth? (ask harder if yes)
- Have I covered all required topics? (check your checklist)

=== EXAMPLE QUESTION PATTERNS ===

For {skills_str}:
- "Can you explain how [concept] works?"
- "In your experience, how have you used [technology]?"
- "What would you do if [scenario]?"
- "Can you walk me through [process]?"
- "Tell me about a time when you [situation]"

=== IMPORTANT REMINDERS ===
- This is VOICE conversation - no markdown, no bullets, speak naturally
- Keep your responses SHORT (1-2 sentences max unless explaining something)
- If candidate asks for clarification, explain in simpler terms
- If candidate goes off-topic, gently redirect
- Sound human, encouraging, professional
- NEVER reveal scores or evaluation to candidate

=== INTERVIEW CLOSURE (VERY IMPORTANT) ===
When you have completed the interview (after asking sufficient questions, typically 8-12 questions or 10-15 minutes):
1. Thank the candidate for their time and responses
2. Summarize that you've gathered enough information  
3. **CRITICAL**: Say clearly "Thank you for completing this interview. Please click the 'End Session' button on your screen to submit your interview for evaluation. We will get back to you with the results soon."
4. Do NOT continue asking questions after this closing statement

BEGIN THE INTERVIEW NOW."""

        return system_instruction
