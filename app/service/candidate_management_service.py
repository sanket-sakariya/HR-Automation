from __future__ import annotations

from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.logger_config import log_user_activity, log_central
from app.config.constants import LogMessages

from app.schema.candidate_management_schema import (
    CandidateCreateSchema,
    CandidateReadSchema,
    CandidateUpdateSchema,
    CandidateListParamsSchema,
)

from app.exception.candidate_management_exception import (
    CandidateNotFoundException,
    CandidateCreationException,
    CandidateUpdateException,
    CandidateDeletionException,
    DuplicateApplicationException,
)

from app.service.baseapp_service import BaseAppService
from app.repository.candidate_repository import CandidateRepository
from app.repository.job_requirement_repository import JobRequirementRepository
from app.repository.candidate_profile_repository import CandidateProfileRepository

from app.exception.job_requirement_exception import JobRequirementNotFoundException

import os
from pathlib import Path


class CandidateManagementService(BaseAppService):
    """Candidate management service for handling job applications."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db)
        self.candidate_repo = CandidateRepository(db=db)
        self.job_requirement_repo = JobRequirementRepository(db=db)
        self.candidate_profile_repo = CandidateProfileRepository(db=db)

    async def create_candidate_application(
        self,
        job_requirement_id: UUID,
        payload: CandidateCreateSchema,
    ) -> CandidateReadSchema:
        """Create a new candidate application."""
        try:
            # Verify job requirement exists
            job_requirement = await self.job_requirement_repo.get_by_id(job_requirement_id)
            if not job_requirement:
                raise JobRequirementNotFoundException(job_requirement_id)

            # Generate candidate_id (since it needs to be unique per job)
            candidate_id = uuid4()

            candidate_data = payload.model_dump()
            candidate_data["candidate_id"] = candidate_id

            # For public applications, set created_by to system user UUID
            # since there's no authenticated user
            system_user_uuid = "00000000-0000-0000-0000-000000000000"
            candidate_data["created_by"] = system_user_uuid

            candidate = await self.candidate_repo.insert(
                candidate_data=candidate_data
            )

            log_user_activity(
                message=f"Candidate application created: {candidate.candidate_id} applied to job {job_requirement_id}",
                action_type="candidate_application_created"
            )

            return CandidateReadSchema.model_validate(candidate)

        except DuplicateApplicationException:
            raise
        except Exception as e:
            log_central(
                f"Error creating candidate application: {str(e)} [job_requirement_id={job_requirement_id}]",
                level="error"
            )
            raise CandidateCreationException(f"Failed to create candidate application: {str(e)}")

    async def get_candidate_by_id(
        self,
        candidate_id: UUID,
    ) -> CandidateReadSchema:
        """Get candidate by ID."""
        candidate = await self.candidate_repo.get_by_id(candidate_id)
        if not candidate:
            raise CandidateNotFoundException(candidate_id)

        return CandidateReadSchema.model_validate(candidate)

    async def update_candidate(
        self,
        candidate_id: UUID,
        payload: CandidateUpdateSchema,
    ) -> CandidateReadSchema:
        """Update candidate information."""
        candidate_data = payload.model_dump(exclude_unset=True)

        candidate = await self.candidate_repo.update(
            candidate_id=candidate_id,
            candidate_data=candidate_data
        )

        log_user_activity(
            message=f"Candidate updated: {candidate.candidate_id}",
            action_type="candidate_updated"
        )

        return CandidateReadSchema.model_validate(candidate)

    async def delete_candidate(
        self,
        candidate_id: UUID,
    ) -> bool:
        """Delete candidate (soft delete)."""
        # Also delete associated profiles
        await self.candidate_profile_repo.delete_by_candidate_id(candidate_id)

        result = await self.candidate_repo.delete(candidate_id)

        log_user_activity(
            message=f"Candidate deleted: {candidate_id}",
            action_type="candidate_deleted"
        )

        return result

    async def get_candidates(
        self,
        params: CandidateListParamsSchema,
    ) -> Dict[str, Any]:
        """Get paginated list of candidates."""
        filters = []

        if params.status:
            filters.append({"field": "status", "operator": "is", "value": params.status.value})

        if params.job_requirement_id:
            filters.append({"field": "job_requirement_id", "operator": "equal_to", "value": str(params.job_requirement_id)})

        return await self.candidate_repo.get_all(
            filters=filters,
            search=params.search,
            skip=(params.page - 1) * params.limit,
            limit=params.limit
        )

    async def get_job_requirement_details(
        self,
        job_requirement_id: UUID,
        workspace_id: UUID,
    ) -> Dict[str, Any]:
        """Get job requirement details for form generation."""
        job_requirement = await self.job_requirement_repo.get_by_id(job_requirement_id, workspace_id)
        if not job_requirement:
            raise JobRequirementNotFoundException(job_requirement_id)

        return {
            "job_requirement_id": job_requirement.job_requirement_id,
            "title": job_requirement.title,
            "department": job_requirement.department,
            "description": job_requirement.description,
            "requirements": job_requirement.requirements,
            "location": job_requirement.location,
            "job_type": job_requirement.job_type,
            "salary_range": job_requirement.salary_range,
            "benefits": job_requirement.benefits,
            "company_name": getattr(job_requirement.company, 'company_name', None) if hasattr(job_requirement, 'company') else None
        }

    def generate_application_form_html(
        self,
        job_details: Dict[str, Any]
    ) -> str:
        """Generate HTML form for job application."""
        html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Apply for {job_details.get('title', 'Job Position')}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{
            background-color: #f8f9fa;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}
        .form-container {{
            max-width: 800px;
            margin: 2rem auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .job-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            text-align: center;
        }}
        .job-details {{
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            margin: 1rem;
            padding: 1rem;
            border-radius: 5px;
        }}
        .form-section {{
            padding: 2rem;
        }}
        .section-title {{
            border-bottom: 2px solid #667eea;
            padding-bottom: 0.5rem;
            margin-bottom: 1.5rem;
            color: #495057;
            font-weight: 600;
        }}
        .btn-submit {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            padding: 12px 30px;
            font-size: 16px;
            border-radius: 25px;
            width: 100%;
            margin-top: 1rem;
        }}
        .btn-submit:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }}
        .skill-tags {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
        }}
        .skill-tag {{
            background: #e9ecef;
            padding: 0.25rem 0.5rem;
            border-radius: 15px;
            font-size: 0.875rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="form-container">
            <!-- Job Details Section -->
            <div class="job-header">
                <h1 class="mb-2">{job_details.get('title', 'Job Position')}</h1>
                <h5 class="mb-0">{job_details.get('department', '')} Department</h5>
                {f"<p class='mt-2 mb-0'>at {job_details.get('company_name', '')}</p>" if job_details.get('company_name') else ""}
            </div>

            <div class="job-details">
                <h5>Job Details</h5>
                <p><strong>Description:</strong> {job_details.get('description', 'N/A')}</p>
                <p><strong>Location:</strong> {job_details.get('location', 'N/A')}</p>
                <p><strong>Job Type:</strong> {job_details.get('job_type', 'N/A')}</p>
                {f"<p><strong>Salary Range:</strong> {job_details.get('salary_range', {}).get('min', 'N/A')} - {job_details.get('salary_range', {}).get('max', 'N/A')}</p>" if job_details.get('salary_range') else ""}
                {f"<p><strong>Benefits:</strong> {', '.join(job_details.get('benefits', []))}</p>" if job_details.get('benefits') else ""}
            </div>

            <!-- Application Form -->
            <form action="/api/candidates/apply" method="POST" enctype="multipart/form-data" class="form-section">
                <input type="hidden" name="job_requirement_id" value="{job_details.get('job_requirement_id', '')}">

                <!-- Personal Information -->
                <h4 class="section-title">Personal Information</h4>
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label for="first_name" class="form-label">First Name *</label>
                        <input type="text" class="form-control" id="first_name" name="first_name" required>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label for="last_name" class="form-label">Last Name *</label>
                        <input type="text" class="form-control" id="last_name" name="last_name" required>
                    </div>
                </div>

                <!-- Contact Information -->
                <h4 class="section-title">Contact Information</h4>
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label for="email" class="form-label">Email Address *</label>
                        <input type="email" class="form-control" id="email" name="email" required>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label for="phone" class="form-label">Phone Number</label>
                        <input type="tel" class="form-control" id="phone" name="phone">
                    </div>
                </div>

                <!-- Professional Information -->
                <h4 class="section-title">Professional Information</h4>
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label for="current_location" class="form-label">Current Location</label>
                        <input type="text" class="form-control" id="current_location" name="current_location">
                    </div>
                    <div class="col-md-6 mb-3">
                        <label for="expected_salary" class="form-label">Expected Salary</label>
                        <input type="number" class="form-control" id="expected_salary" name="expected_salary" step="0.01">
                    </div>
                </div>

                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label for="notice_period" class="form-label">Notice Period</label>
                        <input type="text" class="form-control" id="notice_period" name="notice_period" placeholder="e.g., 30 days">
                    </div>
                    <div class="col-md-6 mb-3">
                        <label for="willing_to_relocate" class="form-label">Willing to Relocate</label>
                        <select class="form-select" id="willing_to_relocate" name="willing_to_relocate">
                            <option value="">Select option</option>
                            <option value="true">Yes</option>
                            <option value="false">No</option>
                        </select>
                    </div>
                </div>

                <!-- Online Presence -->
                <h4 class="section-title">Online Presence</h4>
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label for="linkedin_url" class="form-label">LinkedIn Profile</label>
                        <input type="url" class="form-control" id="linkedin_url" name="linkedin_url" placeholder="https://linkedin.com/in/yourprofile">
                    </div>
                    <div class="col-md-6 mb-3">
                        <label for="portfolio_url" class="form-label">Portfolio Website</label>
                        <input type="url" class="form-control" id="portfolio_url" name="portfolio_url" placeholder="https://yourportfolio.com">
                    </div>
                </div>

                <!-- Skills -->
                <div class="mb-3">
                    <label for="skills" class="form-label">Skills (comma-separated)</label>
                    <input type="text" class="form-control" id="skills" name="skills" placeholder="Python, JavaScript, React, etc.">
                    <div class="form-text">Enter your skills separated by commas</div>
                </div>

                <!-- Resume Upload -->
                <h4 class="section-title">Resume</h4>
                <div class="mb-3">
                    <label for="resume" class="form-label">Upload Resume *</label>
                    <input type="file" class="form-control" id="resume" name="resume" accept=".pdf,.doc,.docx" required>
                    <div class="form-text">Accepted formats: PDF, DOC, DOCX (Max 5MB)</div>
                </div>

                <!-- Submit Button -->
                <button type="submit" class="btn btn-primary btn-submit">
                    <i class="fas fa-paper-plane"></i> Submit Application
                </button>
            </form>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Convert skills input to array format for backend
        document.querySelector('form').addEventListener('submit', function(e) {{
            const skillsInput = document.getElementById('skills');
            if (skillsInput.value) {{
                const skillsArray = skillsInput.value.split(',').map(skill => skill.trim()).filter(skill => skill);
                // Backend will handle parsing this
            }}
        }});
    </script>
</body>
</html>
        """
        return html_template

    async def save_resume_file(
        self,
        file,
        candidate_id: UUID,
        job_requirement_id: UUID
    ) -> str:
        """Save uploaded resume file and return the file path."""
        try:
            # Use absolute path for resume directory
            resume_dir = Path(r"D:\HR automation\interview-management-service\resume")
            resume_dir.mkdir(parents=True, exist_ok=True)

            # Get file extension
            file_extension = Path(file.filename).suffix.lower()

            # Name file using candidate_id only
            filename = f"{candidate_id}{file_extension}"
            file_path = resume_dir / filename

            # Save file
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)

            # Return absolute path
            return str(file_path)

        except Exception as e:
            log_central(
                f"Error saving resume file: {str(e)} [candidate_id={candidate_id}, job_requirement_id={job_requirement_id}]",
                level="error"
            )
            raise CandidateCreationException(f"Failed to save resume: {str(e)}")
