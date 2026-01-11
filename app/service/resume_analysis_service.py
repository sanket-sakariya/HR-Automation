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
        job_details: Dict[str, Any]
    ) -> str:
        """
        Create a highly detailed dynamic prompt based on job requirements.
        
        Args:
            resume_text: Extracted text from candidate's resume
            job_details: Job requirement details including title, description, requirements, etc.
            
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

ANALYSIS INSTRUCTIONS:
======================
Provide a comprehensive, granular evaluation of this candidate for this specific role. Your analysis must be extremely detailed and precise to ensure differentiation between candidates.

Evaluate the candidate on the following dimensions with VERY PRECISE DECIMAL SCORING (use at least 2-4 decimal places):

1. **Skills Match Score (0-25.0000)**: 
   - Evaluate exact match of technical skills, tools, and technologies mentioned in job requirements
   - Consider skill level, proficiency, and recency
   - Account for both required and preferred skills
   - Penalize missing critical skills significantly
   - Bonus for additional relevant skills not mentioned in requirements

2. **Experience Relevance Score (0-25.0000)**:
   - Evaluate years of experience vs required range
   - Assess relevance of previous roles to this position
   - Consider industry alignment
   - Evaluate progression and career growth
   - Weight recent experience more heavily
   - Consider project complexity and impact

3. **Education & Certifications Score (0-15.0000)**:
   - Evaluate degree level and field of study alignment
   - Consider institution reputation (if mentioned)
   - Assess relevant certifications and their recency
   - Evaluate continuous learning and professional development
   - Consider specializations and additional qualifications

4. **Projects & Achievements Score (0-15.0000)**:
   - Evaluate project complexity and scale
   - Assess measurable achievements and outcomes
   - Consider innovation and problem-solving demonstrated
   - Evaluate technical depth shown in projects
   - Assess leadership and collaboration indicators

5. **Cultural & Soft Indicators Score (0-10.0000)**:
   - Evaluate communication skills (from resume quality)
   - Assess leadership indicators
   - Consider teamwork and collaboration mentions
   - Evaluate adaptability and learning agility indicators
   - Consider location compatibility and relocation willingness

6. **Overall Fit Score (0-10.0000)**:
   - Holistic assessment of candidate suitability
   - Consider compensation expectations vs range
   - Evaluate notice period and availability
   - Assess career trajectory alignment
   - Consider any red flags or exceptional qualities

SCORING GRANULARITY REQUIREMENTS:
- Use 4 decimal places for maximum differentiation (e.g., 23.4567, not 23.5)
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
            "score": <0-25.0000>,
            "analysis": "Detailed analysis of skills match with specific examples",
            "matched_skills": ["list of matched skills"],
            "missing_skills": ["list of critical missing skills"],
            "bonus_skills": ["list of additional relevant skills"]
        }},
        "experience_relevance": {{
            "score": <0-25.0000>,
            "analysis": "Detailed analysis of experience relevance",
            "years_of_experience": <number>,
            "relevant_roles": ["list of relevant previous roles"],
            "key_achievements": ["list of notable achievements"]
        }},
        "education_certifications": {{
            "score": <0-15.0000>,
            "analysis": "Detailed analysis of education and certifications",
            "degrees": ["list of degrees"],
            "certifications": ["list of certifications"],
            "continuous_learning": "assessment of ongoing education"
        }},
        "projects_achievements": {{
            "score": <0-15.0000>,
            "analysis": "Detailed analysis of projects and measurable achievements",
            "notable_projects": ["list of relevant projects"],
            "quantified_impact": ["list of measurable outcomes"]
        }},
        "cultural_soft_indicators": {{
            "score": <0-10.0000>,
            "analysis": "Analysis of soft skills and cultural fit indicators",
            "strengths": ["list of observed soft skill strengths"],
            "concerns": ["list of any concerns"]
        }},
        "overall_fit": {{
            "score": <0-10.0000>,
            "analysis": "Holistic fit assessment for this specific role",
            "key_strengths": ["top 3-5 strengths for this role"],
            "key_concerns": ["top concerns or gaps"],
            "recommendation": "Brief hiring recommendation"
        }}
    }},
    "summary": "3-4 sentence executive summary of the candidate's fit for this role",
    "ranking_category": "<Excellent|Strong|Good|Fair|Poor> based on total score",
    "timestamp": "{time.strftime('%Y-%m-%d %H:%M:%S')}"
}}

IMPORTANT: Ensure your scoring is precise and differentiated. Two candidates should rarely have the exact same score.
"""
        
        return prompt

    async def analyze_resume(
        self,
        resume_path: str,
        job_details: Dict[str, Any],
        candidate_id: UUID,
        job_requirement_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze a candidate's resume against job requirements using AI.
        
        Args:
            resume_path: Path to the resume PDF file
            job_details: Job requirement details
            candidate_id: UUID of the candidate
            job_requirement_id: UUID of the job requirement
            
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

            # Create dynamic prompt based on job requirements
            prompt = self.create_dynamic_prompt(resume_text, job_details)

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

