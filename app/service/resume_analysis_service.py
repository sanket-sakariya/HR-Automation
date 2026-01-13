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
        
        # Format experience requirements
        experience_text = ""
        if experience:
            min_years = experience.get('minYears', experience.get('min_years', 0))
            max_years = experience.get('maxYears', experience.get('max_years', 'N/A'))
            preferred = experience.get('preferred', '')
            experience_text = f"Required Experience: {min_years}-{max_years} years"
            if preferred:
                experience_text += f"\nPreferred: {preferred}"
        
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
        
        # Create the detailed prompt
        prompt = f"""
You are an expert HR recruiter and resume analyst. Analyze the following candidate's resume for the position of "{job_title}" in the {department} department.

JOB DETAILS:
=============
Position: {job_title}
Department: {department}
Location: {location}
Job Type: {job_type}

Job Description:
{description}

{requirements_text}

{experience_text}

Salary Range: {salary_range.get('min', 'N/A')} - {salary_range.get('max', 'N/A')} {salary_range.get('currency', '')}

CANDIDATE'S RESUME:
===================
{resume_text}
{candidate_info_text}

ANALYSIS INSTRUCTIONS:
======================
Provide a comprehensive, granular evaluation of this candidate for this specific role. Your analysis must be extremely detailed and precise to ensure differentiation between candidates.

⚠️ CRITICAL SCORING PRIORITIES:
- Skills and Experience are THE MOST IMPORTANT factors (60% of total score)
- Projects demonstrate practical application (25% of total score)
- Other factors are secondary considerations (15% of total score)

Evaluate the candidate on the following dimensions with VERY PRECISE DECIMAL SCORING (use at least 2-4 decimal places):

1. **Skills Match Score (0-30.0000)** [30% WEIGHT - HIGHEST PRIORITY]: 
   - THIS IS A CRITICAL EVALUATION FACTOR
   - Evaluate BOTH resume content AND form-submitted skills list
   - Cross-reference: Do resume projects/experience validate the claimed skills?
   - Consider skill level, proficiency, and recency of each skill
   - Account for both required and preferred skills
   - Penalize missing critical required skills significantly (-3 to -5 points per missing skill)
   - Bonus for additional relevant skills not mentioned in requirements (+0.5 to +2 points)
   - Deep technical skills should score higher than breadth
   - Recent usage and current versions matter significantly
   - Hands-on experience weighted more than theoretical knowledge
   - If form skills match resume evidence = higher credibility score

2. **Experience Relevance Score (0-30.0000)** [30% WEIGHT - HIGHEST PRIORITY]:
   - THIS IS A CRITICAL EVALUATION FACTOR
   - Evaluate years of experience vs required range (exact match = full points)
   - Assess direct relevance of previous roles to this specific position
   - Consider industry alignment and domain expertise
   - Evaluate career progression and growth trajectory
   - Weight recent experience (last 2-3 years) more heavily than older experience
   - Consider project complexity, team size, and impact delivered
   - Leadership experience and ownership of outcomes matter
   - Consistency and stability in career path is a plus

3. **Projects & Achievements Score (0-25.0000)** [25% WEIGHT - MAJOR PRIORITY]:
   - THIS IS A MAJOR EVALUATION FACTOR
   - Evaluate project complexity, scale, and technical depth
   - Assess measurable achievements with quantified outcomes (metrics, percentages, numbers)
   - Consider innovation, problem-solving approach, and creativity demonstrated
   - Evaluate technical challenges overcome and solutions implemented
   - Assess leadership, collaboration, and ownership in projects
   - Open-source contributions and side projects are valuable
   - Real-world production experience weighted higher than academic projects
   - Business impact and user scale matter significantly

4. **Education & Certifications Score (0-8.0000)** [8% WEIGHT - SECONDARY]:
   - Evaluate degree level and field of study alignment with role
   - Consider institution reputation if mentioned (minor factor)
   - Assess relevant certifications and their recency
   - Evaluate continuous learning and professional development initiatives
   - Consider specialized training and additional qualifications
   - Note: Experience and skills outweigh education for technical roles

5. **Cultural & Soft Indicators Score (0-4.0000)** [4% WEIGHT - SECONDARY]:
   - Evaluate communication skills based on resume quality and clarity
   - Assess leadership indicators and initiative-taking
   - Consider teamwork and collaboration mentions
   - Evaluate adaptability and learning agility indicators
   - Consider location compatibility and relocation willingness

6. **Overall Fit Score (0-3.0000)** [3% WEIGHT - SECONDARY]:
   - Holistic assessment of candidate suitability for role and company
   - Consider compensation expectations vs offered range (use form salary data)
   - Evaluate notice period and immediate availability (use form data)
   - Consider location match and relocation willingness (use form data)
   - Assess career trajectory alignment with role growth path
   - Consider any red flags or exceptional standout qualities

SCORING GRANULARITY REQUIREMENTS:
- Use 4 decimal places for maximum differentiation (e.g., 28.4567, not 28.5)
- Each sub-criterion should have micro-adjustments based on specifics
- Consider nuanced factors like specific tools, frameworks, versions mentioned
- Account for keyword matches, context, and depth of experience
- Factor in recency, frequency, and emphasis of skills mentioned
- Apply penalties for gaps, mismatches, or missing critical elements
- Apply bonuses for exceptional achievements, unique combinations, or overqualifications

Return your response in the following JSON format ONLY (no additional text):
{{
    "total_score": <precise decimal sum of all scores, max 100.0000>,
    "breakdown": {{
        "skills_match": {{
            "score": <0-30.0000>,
            "weight": "30%",
            "analysis": "Detailed analysis of skills match with specific examples from resume",
            "matched_skills": ["list of matched skills with proficiency level"],
            "missing_skills": ["list of critical missing required skills"],
            "bonus_skills": ["list of additional relevant skills beyond requirements"]
        }},
        "experience_relevance": {{
            "score": <0-30.0000>,
            "weight": "30%",
            "analysis": "Detailed analysis of experience relevance and career trajectory",
            "years_of_experience": <number>,
            "relevant_roles": ["list of directly relevant previous roles"],
            "key_achievements": ["list of notable achievements with quantified impact"]
        }},
        "projects_achievements": {{
            "score": <0-25.0000>,
            "weight": "25%",
            "analysis": "Detailed analysis of projects, technical depth, and measurable achievements",
            "notable_projects": ["list of significant projects with scale/impact"],
            "quantified_impact": ["list of measurable outcomes with numbers/metrics"],
            "technical_complexity": "assessment of technical sophistication demonstrated"
        }},
        "education_certifications": {{
            "score": <0-8.0000>,
            "weight": "8%",
            "analysis": "Analysis of education background and certifications",
            "degrees": ["list of degrees with field of study"],
            "certifications": ["list of relevant certifications with dates"],
            "continuous_learning": "assessment of ongoing education and skill development"
        }},
        "cultural_soft_indicators": {{
            "score": <0-4.0000>,
            "weight": "4%",
            "analysis": "Analysis of soft skills and cultural fit indicators",
            "strengths": ["list of observed soft skill strengths"],
            "concerns": ["list of any soft skill concerns if applicable"]
        }},
        "overall_fit": {{
            "score": <0-3.0000>,
            "weight": "3%",
            "analysis": "Holistic fit assessment for this specific role",
            "key_strengths": ["top 3-5 strengths for this role"],
            "key_concerns": ["top concerns or gaps if any"],
            "recommendation": "Brief hiring recommendation (Strong Hire/Hire/Maybe/No Hire)"
        }}
    }},
    "summary": "3-4 sentence executive summary emphasizing skills and experience fit for this role",
    "ranking_category": "<Excellent|Strong|Good|Fair|Poor> based on total score",
    "hiring_priority": "<High|Medium|Low> based on skills and experience match",
    "timestamp": "{time.strftime('%Y-%m-%d %H:%M:%S')}"
}}

CRITICAL REMINDERS:
- Skills (30%) and Experience (30%) = 60% of total score - BE STRICT AND DETAILED HERE
- Projects (25%) demonstrate practical application - LOOK FOR QUANTIFIED RESULTS
- Education (8%) + Soft Skills (4%) + Overall Fit (3%) = 15% - SECONDARY FACTORS
- Use 4 decimal precision to ensure unique scores for each candidate
- Two candidates should rarely have identical scores even if similar backgrounds
- IMPORTANT: Cross-validate form-submitted skills with resume evidence
- Form data provides additional context - use it to enhance, not replace resume analysis
- Salary expectations, notice period, and relocation willingness affect Overall Fit score
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

            # Add metadata
            analysis_result['metadata'] = {
                'candidate_id': str(candidate_id),
                'job_requirement_id': str(job_requirement_id),
                'processing_time': processing_time,
                'input_tokens': response.usage_metadata.prompt_token_count,
                'output_tokens': response.usage_metadata.candidates_token_count,
                'total_tokens': response.usage_metadata.total_token_count,
                'resume_length': len(resume_text),
                'analysis_timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }

            log_central(
                f"Resume analysis completed successfully: Score={analysis_result.get('total_score', 'N/A')}, "
                f"Time={processing_time:.2f}s, Tokens={response.usage_metadata.total_token_count} "
                f"[candidate_id={candidate_id}]",
                level="info"
            )

            # Print token usage to terminal
            print("\n" + "="*60)
            print("🤖 AI RESUME ANALYSIS - TOKEN USAGE")
            print("="*60)
            print(f"📥 Input Tokens:  {response.usage_metadata.prompt_token_count:,}")
            print(f"📤 Output Tokens: {response.usage_metadata.candidates_token_count:,}")
            print(f"📊 Total Tokens:  {response.usage_metadata.total_token_count:,}")
            print(f"⏱️  Processing Time: {processing_time:.2f}s")
            print(f"📝 Resume Score: {analysis_result.get('total_score', 'N/A')}")
            print("="*60 + "\n")

            return analysis_result

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

