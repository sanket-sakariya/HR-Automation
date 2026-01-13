"""Resume Analysis Service - AI-powered resume evaluation based on job requirements."""

from __future__ import annotations

import json
import time
from typing import Dict, Any, Optional
from pathlib import Path
from uuid import UUID

try:
    import google.generativeai as genai
    from pypdf import PdfReader
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from app.config.logger_config import log_central


class ResumeAnalysisService:
    """Service for analyzing resumes using AI based on job requirements."""

    def __init__(self, gemini_api_key: Optional[str] = None):
        """Initialize the resume analysis service."""
        self.gemini_api_key = gemini_api_key or "AIzaSyDHNd6W382fBzwf_HbPxf70sxG13XE9xgA"
        
        if GEMINI_AVAILABLE and self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
        else:
            self.model = None
            log_central(
                "Gemini API not configured. Resume analysis will be skipped.",
                level="warning"
            )

    def extract_text_from_pdf(self, pdf_path: str) -> Optional[str]:
        """
        Extract text content from PDF resume.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Extracted text content or None if failed
        """
        try:
            if not GEMINI_AVAILABLE:
                log_central("pypdf not available. Cannot extract PDF text.", level="error")
                return None

            reader = PdfReader(pdf_path)
            text_content = ""
            
            # Extract text from all pages
            for page in reader.pages:
                text_content += page.extract_text() + "\n\n"
            
            return text_content.strip()
        
        except Exception as e:
            log_central(f"Error extracting text from PDF: {str(e)}", level="error")
            return None

    def create_dynamic_prompt(
        self,
        resume_text: str,
        job_details: Dict[str, Any],
        candidate_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a highly detailed dynamic prompt based on job requirements and candidate data.
        
        Args:
            resume_text: Extracted text from candidate's resume
            job_details: Job requirement details including title, description, requirements, etc.
            candidate_data: Additional candidate information from application form
            
        Returns:
            Formatted prompt for AI analysis
        """
        # Extract job details
        job_title = job_details.get('title', 'Position')
        department = job_details.get('department', 'N/A')
        description = job_details.get('description', 'N/A')
        requirements = job_details.get('requirements', [])
        experience = job_details.get('experience', {})
        location = job_details.get('location', 'N/A')
        job_type = job_details.get('job_type', 'N/A')
        salary_range = job_details.get('salary_range', {})
        
        # Format requirements list
        requirements_text = ""
        if requirements:
            requirements_text = "Job Requirements:\n"
            for idx, req in enumerate(requirements, 1):
                if isinstance(req, dict):
                    skill = req.get('skill', req.get('requirement', 'N/A'))
                    level = req.get('level', 'N/A')
                    required = req.get('required', True)
                    requirements_text += f"  {idx}. {skill} - Level: {level} - {'Required' if required else 'Preferred'}\n"
                else:
                    requirements_text += f"  {idx}. {req}\n"
        
        # Format experience requirements with proper handling of null values
        experience_text = ""
        if experience:
            min_years = experience.get('minYears', experience.get('min_years'))
            max_years = experience.get('maxYears', experience.get('max_years'))
            preferred = experience.get('preferred', '')
            
            # Format experience based on min/max availability
            if min_years is not None and max_years is not None:
                experience_text = f"Required Experience: {min_years} to {max_years} years"
            elif min_years is not None and max_years is None:
                if min_years == 0:
                    experience_text = "Required Experience: 0+ years (Freshers welcome)"
                else:
                    experience_text = f"Required Experience: {min_years}+ years"
            elif min_years is None and max_years is not None:
                experience_text = f"Required Experience: 0 to {max_years} years"
            else:
                experience_text = "Experience: Not specified"
            
            if preferred:
                experience_text += f"\nPreferred Experience: {preferred}"
        
        # Format candidate data from application form (if provided)
        candidate_info_text = ""
        if candidate_data:
            candidate_info_text = "\n\nCANDIDATE APPLICATION FORM DATA:\n================================\n"
            
            if candidate_data.get('first_name') or candidate_data.get('last_name'):
                name = f"{candidate_data.get('first_name', '')} {candidate_data.get('last_name', '')}".strip()
                candidate_info_text += f"Name: {name}\n"
            
            if candidate_data.get('email'):
                candidate_info_text += f"Email: {candidate_data.get('email')}\n"
            
            if candidate_data.get('phone'):
                candidate_info_text += f"Phone: {candidate_data.get('phone')}\n"
            
            if candidate_data.get('skills'):
                skills_list = candidate_data.get('skills')
                if isinstance(skills_list, list):
                    candidate_info_text += f"Skills (Self-Reported): {', '.join(skills_list)}\n"
                else:
                    candidate_info_text += f"Skills (Self-Reported): {skills_list}\n"
            
            if candidate_data.get('expected_salary'):
                candidate_info_text += f"Expected Salary: {candidate_data.get('expected_salary')}\n"
            
            if candidate_data.get('notice_period'):
                candidate_info_text += f"Notice Period: {candidate_data.get('notice_period')}\n"
            
            if candidate_data.get('current_location'):
                candidate_info_text += f"Current Location: {candidate_data.get('current_location')}\n"
            
            if candidate_data.get('willing_to_relocate') is not None:
                willing = "Yes" if candidate_data.get('willing_to_relocate') else "No"
                candidate_info_text += f"Willing to Relocate: {willing}\n"
            
            if candidate_data.get('linkedin_url'):
                candidate_info_text += f"LinkedIn: {candidate_data.get('linkedin_url')}\n"
            
            if candidate_data.get('portfolio_url'):
                candidate_info_text += f"Portfolio: {candidate_data.get('portfolio_url')}\n"
            
            candidate_info_text += "\nNote: Use both resume content AND form data for comprehensive evaluation.\n"
        
        # Create the powerful, comprehensive prompt using ALL job requirement parameters
        prompt = f"""
You are an EXPERT HR RECRUITER and TECHNICAL EVALUATOR with 15+ years of experience. Your task is to perform a COMPREHENSIVE, STRICT, and DETAILED evaluation of a candidate's resume against ALL job requirements.

═══════════════════════════════════════════════════════════════
POSITION OVERVIEW
═══════════════════════════════════════════════════════════════
🎯 Position: {job_title}
🏢 Department: {department}
📍 Location: {location}
💼 Job Type: {job_type}
💰 Salary Range: {salary_range.get('min', 'N/A')} - {salary_range.get('max', 'N/A')} {salary_range.get('currency', 'INR')}

═══════════════════════════════════════════════════════════════
DETAILED JOB DESCRIPTION
═══════════════════════════════════════════════════════════════
{description}

═══════════════════════════════════════════════════════════════
MANDATORY REQUIREMENTS - STRICT COMPARISON REQUIRED
═══════════════════════════════════════════════════════════════
{requirements_text}

⚠️ CRITICAL: Every single requirement listed above must be STRICTLY evaluated against the candidate's resume. Each missing or weak skill significantly impacts the score.

═══════════════════════════════════════════════════════════════
EXPERIENCE REQUIREMENTS - MUST MATCH
═══════════════════════════════════════════════════════════════
{experience_text}

Evaluate:
- Does the candidate have the required years of experience?
- Are their past roles directly relevant to this position?
- Do they have progressive career growth?
- Have they worked on similar technologies/domains?

═══════════════════════════════════════════════════════════════
CANDIDATE'S RESUME - COMPLETE CONTENT
═══════════════════════════════════════════════════════════════
{resume_text}

═══════════════════════════════════════════════════════════════
CANDIDATE'S APPLICATION FORM DATA - CROSS-VALIDATE WITH RESUME
═══════════════════════════════════════════════════════════════
{candidate_info_text}

⚠️ IMPORTANT: Cross-validate form-submitted skills with actual resume content. If skills claimed in form are not evident in resume, apply penalty.

═══════════════════════════════════════════════════════════════
COMPREHENSIVE SCORING FRAMEWORK (0-10000 INTEGER SCALE)
═══════════════════════════════════════════════════════════════

🎯 **1. SKILLS MATCH SCORE (0-3000) [30% - HIGHEST PRIORITY]**

STRICT EVALUATION CRITERIA:
✓ Required Skills Presence: Does resume show ALL required skills?
✓ Proficiency Level: Do skills match required levels (beginner/intermediate/advanced)?
✓ Hands-on Evidence: Are skills backed by projects/experience or just listed?
✓ Recency: Are skills currently used or outdated?
✓ Depth vs Breadth: Deep expertise vs surface-level knowledge
✓ Technology Versions: Current frameworks/tools vs legacy versions
✓ Form-Resume Validation: Do self-reported skills match resume evidence?

SCORING GUIDE:
- Perfect match (all required + advanced level + proven): 2700-3000
- Strong match (most required + intermediate+ level): 2200-2699
- Good match (required skills + some gaps): 1700-2199
- Moderate match (missing some required skills): 1200-1699
- Weak match (missing many required skills): 600-1199
- Poor match (mostly missing skills): 100-599

PENALTIES:
- Each missing REQUIRED skill: -150 to -300 points
- Claimed but not proven in resume: -100 points per skill
- Outdated technology versions: -50 to -150 points

BONUSES:
- Extra relevant skills beyond requirements: +50 to +200 points
- Expert-level certifications: +100 to +250 points
- Cutting-edge technology adoption: +50 to +150 points

🎯 **2. EXPERIENCE RELEVANCE SCORE (0-3000) [30% - HIGHEST PRIORITY]**

STRICT EVALUATION CRITERIA:
✓ Years Match: Does experience fall within required range?
✓ Role Relevance: Are previous job titles/roles directly relevant?
✓ Industry Alignment: Same or related industry experience?
✓ Project Complexity: Handled projects of similar or greater complexity?
✓ Team Leadership: Led teams if leadership is required?
✓ Career Progression: Consistent growth or lateral moves?
✓ Employment Gaps: Any unexplained gaps in career?
✓ Domain Expertise: Deep knowledge in required domain?

SCORING GUIDE:
- Perfect fit (exact years + highly relevant roles + leadership): 2700-3000
- Strong fit (within range + relevant roles): 2200-2699
- Good fit (close to range + related roles): 1700-2199
- Moderate fit (some relevance + gaps): 1200-1699
- Weak fit (limited relevance): 600-1199
- Poor fit (mostly irrelevant): 100-599

🎯 **3. PROJECTS & ACHIEVEMENTS SCORE (0-2500) [25% - MAJOR PRIORITY]**

STRICT EVALUATION CRITERIA:
✓ Project Complexity: Technical sophistication and scale
✓ Quantified Impact: Metrics, percentages, numbers proving impact
✓ Problem-Solving: Challenging problems solved
✓ Technologies Used: Alignment with job requirements
✓ Team Size: Solo vs team projects
✓ Business Impact: Revenue, users, performance improvements
✓ Innovation: Novel solutions or approaches
✓ Open Source: Contributions to community projects

SCORING GUIDE:
- Outstanding (complex + quantified + innovative): 2200-2500
- Excellent (solid projects + measurable impact): 1800-2199
- Good (decent projects + some metrics): 1400-1799
- Moderate (basic projects + limited impact): 900-1399
- Weak (minimal projects): 400-899
- Poor (no significant projects): 100-399

🎯 **4. EDUCATION & CERTIFICATIONS SCORE (0-800) [8% - SECONDARY]**

STRICT EVALUATION CRITERIA:
✓ Degree Level: Bachelor's, Master's, PhD alignment with requirements
✓ Field of Study: Computer Science, Engineering, related fields
✓ Relevant Certifications: Industry-recognized certifications
✓ Continuous Learning: Recent courses, training, upskilling
✓ Academic Achievements: Honors, publications, research

SCORING GUIDE:
- Excellent (advanced degree + certifications + learning): 700-800
- Good (relevant degree + some certifications): 550-699
- Moderate (basic degree + limited certifications): 350-549
- Weak (degree but not related field): 200-349
- Minimal (basic education only): 100-199

🎯 **5. CULTURAL & SOFT SKILLS SCORE (0-400) [4% - SECONDARY]**

STRICT EVALUATION CRITERIA:
✓ Communication: Resume clarity, presentation quality
✓ Leadership: Evidence of leading teams/initiatives
✓ Collaboration: Team projects, cross-functional work
✓ Adaptability: Multiple technologies, changing roles
✓ Initiative: Self-started projects, proactive approach

SCORING GUIDE:
- Excellent (strong evidence across all areas): 350-400
- Good (clear evidence in most areas): 280-349
- Moderate (some evidence): 210-279
- Weak (limited evidence): 130-209
- Minimal (barely visible): 100-129

🎯 **6. OVERALL FIT SCORE (0-300) [3% - HOLISTIC]**

STRICT EVALUATION CRITERIA:
✓ Salary Expectations: Within or close to offered range?
✓ Location Match: Same location or willing to relocate?
✓ Notice Period: Can join in required timeframe?
✓ Career Goals: Aligned with role growth path?
✓ Red Flags: Job hopping, gaps, inconsistencies?
✓ Availability: Immediate vs delayed joining

SCORING GUIDE:
- Perfect fit (all factors align): 270-300
- Strong fit (most factors align): 220-269
- Good fit (reasonable alignment): 170-219
- Moderate fit (some concerns): 120-169
- Weak fit (multiple concerns): 100-119

═══════════════════════════════════════════════════════════════
⚠️ CRITICAL SCORING RULES - MUST FOLLOW ⚠️
═══════════════════════════════════════════════════════════════

1. **USE ALL DIGITS - NO ZEROS ALLOWED**: 
   ❌ BAD: 2000, 1500, 800, 3000, 2500
   ✅ GOOD: 2347, 1582, 847, 2891, 2456
   
   Every score MUST use varied digits. Avoid round numbers or trailing zeros.

2. **GRANULAR SCORING**: 
   Score with precision. Two similar candidates should have different scores.
   Use the FULL range: 2347, 2856, 1923, NOT just 2000, 2500, 2000.

3. **STRICT PENALTIES**:
   - Missing required skills = major penalty
   - Unproven claims = penalty
   - Experience mismatch = penalty
   - Employment gaps = penalty

4. **COMPARATIVE EVALUATION**:
   Compare EACH job requirement item against resume evidence
   If requirement is not explicitly found in resume, apply penalty

5. **CROSS-VALIDATION**:
   Form skills vs Resume evidence - must match
   Claimed years vs actual project timelines - must align

═══════════════════════════════════════════════════════════════
OUTPUT FORMAT - RETURN ONLY THIS JSON (NO OTHER TEXT)
═══════════════════════════════════════════════════════════════

{{
    "skills_match": <integer 100-3000, use all digits, no zeros>,
    "experience_relevance": <integer 100-3000, use all digits, no zeros>,
    "projects_achievements": <integer 100-2500, use all digits, no zeros>,
    "education_certifications": <integer 100-800, use all digits, no zeros>,
    "cultural_soft_skills": <integer 100-400, use all digits, no zeros>,
    "overall_fit": <integer 100-300, use all digits, no zeros>,
    "total_score": <sum of all above, max 10000>,
    "recommendation": "<Strong Hire|Hire|Maybe|No Hire>"
}}

REMEMBER: Be STRICT, DETAILED, and PRECISE. Use ALL DIGITS in scores (e.g., 2347 not 2300). Compare EVERY requirement against the resume!
"""
        
        return prompt

    async def analyze_resume(
        self,
        resume_path: str,
        job_details: Dict[str, Any],
        candidate_id: UUID,
        job_requirement_id: UUID,
        candidate_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze a candidate's resume against job requirements using AI.
        
        Args:
            resume_path: Path to the resume PDF file
            job_details: Job requirement details
            candidate_id: UUID of the candidate
            job_requirement_id: UUID of the job requirement
            candidate_data: Additional candidate information from application form (optional)
            
        Returns:
            Analysis results including detailed score and breakdown, or None if failed
        """
        try:
            if not self.model or not GEMINI_AVAILABLE:
                log_central(
                    f"Resume analysis skipped - Gemini not configured [candidate_id={candidate_id}]",
                    level="warning"
                )
                return None

            # Extract text from PDF
            log_central(
                f"Extracting text from resume [candidate_id={candidate_id}]",
                level="info"
            )
            resume_text = self.extract_text_from_pdf(resume_path)
            
            if not resume_text:
                log_central(
                    f"Failed to extract text from resume [candidate_id={candidate_id}]",
                    level="error"
                )
                return None

            # Create dynamic prompt based on job requirements and candidate data
            prompt = self.create_dynamic_prompt(resume_text, job_details, candidate_data)

            # Track processing time
            start_time = time.time()
            
            log_central(
                f"Sending resume to Gemini for analysis [candidate_id={candidate_id}, job_requirement_id={job_requirement_id}]",
                level="info"
            )

            # Generate analysis using Gemini
            response = self.model.generate_content(prompt)
            
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
            
            analysis_result = json.loads(response_text.strip())

            # Convert scores from 0-10000 scale to 0-100 scale with 4 decimal precision
            # This gives us precise float values like 67.5089
            raw_total_score = analysis_result.get('total_score', 0)
            converted_score = round(raw_total_score / 100, 4)  # Divide by 100 to get 0-100 range with 4 decimals
            
            # Convert individual scores as well
            breakdown = {
                'skills_match': round(analysis_result.get('skills_match', 0) / 100, 4),
                'experience_relevance': round(analysis_result.get('experience_relevance', 0) / 100, 4),
                'projects_achievements': round(analysis_result.get('projects_achievements', 0) / 100, 4),
                'education_certifications': round(analysis_result.get('education_certifications', 0) / 100, 4),
                'cultural_soft_skills': round(analysis_result.get('cultural_soft_skills', 0) / 100, 4),
                'overall_fit': round(analysis_result.get('overall_fit', 0) / 100, 4)
            }

            # Reconstruct analysis result with converted scores
            converted_result = {
                'total_score': converted_score,
                'raw_total_score': raw_total_score,  # Keep raw score for reference
                'breakdown': breakdown,
                'recommendation': analysis_result.get('recommendation', 'Maybe'),
                'metadata': {
                    'candidate_id': str(candidate_id),
                    'job_requirement_id': str(job_requirement_id),
                    'processing_time': processing_time,
                    'input_tokens': response.usage_metadata.prompt_token_count,
                    'output_tokens': response.usage_metadata.candidates_token_count,
                    'total_tokens': response.usage_metadata.total_token_count,
                    'resume_length': len(resume_text),
                    'analysis_timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                }
            }

            log_central(
                f"Resume analysis completed successfully: Raw Score={raw_total_score}/10000, "
                f"Converted Score={converted_score}/100, Time={processing_time:.2f}s, "
                f"Tokens={response.usage_metadata.total_token_count} [candidate_id={candidate_id}]",
                level="info"
            )

            # Print token usage and scores to terminal
            print("\n" + "="*70)
            print("🤖 AI RESUME ANALYSIS - TOKEN USAGE & SCORING")
            print("="*70)
            print(f"📥 Input Tokens:      {response.usage_metadata.prompt_token_count:,}")
            print(f"📤 Output Tokens:     {response.usage_metadata.candidates_token_count:,}")
            print(f"📊 Total Tokens:      {response.usage_metadata.total_token_count:,}")
            print(f"⏱️  Processing Time:   {processing_time:.2f}s")
            print("-"*70)
            print(f"📝 Raw Score (0-10000):      {raw_total_score:,}")
            print(f"✨ Final Score (0-100):      {converted_score}")
            print(f"💡 Recommendation:           {converted_result['recommendation']}")
            print("-"*70)
            print(f"   Skills Match:             {breakdown['skills_match']}/30")
            print(f"   Experience Relevance:     {breakdown['experience_relevance']}/30")
            print(f"   Projects & Achievements:  {breakdown['projects_achievements']}/25")
            print(f"   Education:                {breakdown['education_certifications']}/8")
            print(f"   Cultural Fit:             {breakdown['cultural_soft_skills']}/4")
            print(f"   Overall Fit:              {breakdown['overall_fit']}/3")
            print("="*70 + "\n")

            return converted_result

        except json.JSONDecodeError as e:
            log_central(
                f"Failed to parse Gemini response: {str(e)} [candidate_id={candidate_id}]",
                level="error"
            )
            return None
        except Exception as e:
            log_central(
                f"Error analyzing resume: {str(e)} [candidate_id={candidate_id}, job_requirement_id={job_requirement_id}]",
                level="error"
            )
            return None

    def get_ranking_category(self, total_score: float) -> str:
        """
        Convert total score to ranking category.
        
        Args:
            total_score: Total score out of 100
            
        Returns:
            Ranking category string
        """
        if total_score >= 85.0:
            return "Excellent"
        elif total_score >= 70.0:
            return "Strong"
        elif total_score >= 55.0:
            return "Good"
        elif total_score >= 40.0:
            return "Fair"
        else:
            return "Poor"

    def get_hiring_priority(self, skills_score: float, experience_score: float) -> str:
        """
        Determine hiring priority based on skills and experience scores (60% of total).
        
        Args:
            skills_score: Skills match score out of 30
            experience_score: Experience relevance score out of 30
            
        Returns:
            Priority level string
        """
        combined_score = skills_score + experience_score  # Out of 60
        
        if combined_score >= 50.0:  # 83%+ of skills+experience
            return "High"
        elif combined_score >= 40.0:  # 67%+ of skills+experience
            return "Medium"
        else:
            return "Low"

