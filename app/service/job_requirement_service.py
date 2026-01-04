from __future__ import annotations

from typing import Optional, Dict, Any, List, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.logger_config import log_user_activity, log_central
from app.config.constants import LogMessages

from app.schema.job_requirement_schema import (
    JobRequirementCreateSchema,
    JobRequirementUpdateSchema,
    JobRequirementReadSchema,
    JobRequirementStatus,
)

from app.exception.job_requirement_exception import (
    JobRequirementNotFoundException,
    JobRequirementCreationException,
    JobRequirementUpdateException,
    JobRequirementDeletionException,
    JobRequirementInvalidDataException,
)

from app.service.baseapp_service import BaseAppService
from app.repository.job_requirement_repository import JobRequirementRepository
from app.repository.company_repository import CompanyRepository
from app.exception.company_management_exception import CompanyNotFoundException


class JobRequirementService(BaseAppService):
    """Job requirement service for managing job requirements."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db)
        self.job_requirement_repo = JobRequirementRepository(db=db)
        self.company_repo = CompanyRepository(db=db)

    async def create_job_requirement(
        self,
        company_id: UUID,
        payload: JobRequirementCreateSchema,
        user_id: UUID,
        workspace_id: UUID,
    ) -> JobRequirementReadSchema:
        """Create a new job requirement."""

        job_requirement_data = payload.model_dump()
        job_requirement_data["company_id"] = company_id

        # Ensure the company exists
        company = await self.company_repo.get_by_id(company_id, workspace_id)
        if not company:
            raise CompanyNotFoundException(company_id=company_id)

        job_requirement = await self.job_requirement_repo.insert(
            job_requirement_data=job_requirement_data,
            user_id=user_id,
            workspace_id=workspace_id
        )

        log_user_activity(
            f"Job requirement created: {job_requirement.title} for company {company.company_name}",
            action_type="job_requirement_create",
            level="info",
        )

        return JobRequirementReadSchema.model_validate(job_requirement)

    async def create_job_requirement_with_linkedin_data(
        self,
        company_id: UUID,
        payload: JobRequirementCreateSchema,
        user_id: UUID,
        workspace_id: UUID,
    ) -> Tuple[JobRequirementReadSchema, Dict[str, Any]]:
        """Create a new job requirement and return LinkedIn posting data."""

        # Create the job requirement
        job_data = await self.create_job_requirement(
            company_id=company_id,
            payload=payload,
            user_id=user_id,
            workspace_id=workspace_id
        )

        # Get company details for LinkedIn posting (we already validated it exists)
        company = await self.company_repo.get_by_id(company_id, workspace_id)

        # Prepare job data for LinkedIn posting
        linkedin_job_data = {
            "job_requirement_id": str(job_data.job_requirement_id),
            "company_id": str(job_data.company_id),
            "company_name": company.company_name if company else "Our Company",
            "title": job_data.title,
            "department": job_data.department,
            "description": job_data.description,
            "requirements": [{"skill": req.skill, "level": req.level, "required": req.required} for req in job_data.requirements],
            "experience": {
                "min_years": job_data.experience.min_years if job_data.experience else None,
                "max_years": job_data.experience.max_years if job_data.experience else None,
                "preferred": job_data.experience.preferred if job_data.experience else None,
            } if job_data.experience else None,
            "location": job_data.location,
            "job_type": job_data.job_type,
            "salary_range": {
                "min": job_data.salary_range.min if job_data.salary_range else None,
                "max": job_data.salary_range.max if job_data.salary_range else None,
                "currency": job_data.salary_range.currency if job_data.salary_range else "USD",
            } if job_data.salary_range else None,
            "benefits": job_data.benefits,
            "status": job_data.status.value,
            "is_active": job_data.is_active,
            "created_at": job_data.created_at.isoformat() if job_data.created_at else None,
            "updated_at": job_data.updated_at.isoformat() if job_data.updated_at else None,
        }

        return job_data, linkedin_job_data

    async def get_job_requirement(
        self, job_requirement_id: UUID, user_id: UUID, workspace_id: UUID
    ) -> JobRequirementReadSchema:
        """Get a job requirement by ID."""
        job_requirement = await self.job_requirement_repo.get_by_id(
            job_requirement_id=job_requirement_id, workspace_id=workspace_id
        )
        if not job_requirement:
            raise JobRequirementNotFoundException(job_requirement_id=job_requirement_id)
        return JobRequirementReadSchema.model_validate(job_requirement)

    async def list_job_requirements(
        self,
        company_id: Optional[UUID] = None,
        status: Optional[JobRequirementStatus] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        search: Optional[str] = None,
        order_by: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
        user_id: Optional[UUID] = None,
        workspace_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """List job requirements with optional company filter."""

        # Add company filter if specified
        if company_id:
            company_filter = {"column": "company_id", "operator": "eq", "value": str(company_id)}
            if filters:
                filters.append(company_filter)
            else:
                filters = [company_filter]

        # Add status filter if specified
        if status:
            status_filter = {"column": "status", "operator": "eq", "value": status.value}
            if filters:
                filters.append(status_filter)
            else:
                filters = [status_filter]

        result = await self.job_requirement_repo.get_all(
            filters=filters,
            search=search,
            order_by=order_by,
            skip=skip,
            limit=limit,
            user_id=user_id,
            workspace_id=workspace_id,
        )

        # Convert data to schema objects while preserving pagination structure
        if isinstance(result, dict):
            data = result.get("data", [])
            pagination = result.get("pagination", {})
            schema_data = [
                JobRequirementReadSchema.model_validate(job_req) for job_req in data
            ]
            return {"data": schema_data, "pagination": pagination}

        # Fallback for non-dict results
        schema_data = [
            JobRequirementReadSchema.model_validate(job_req) for job_req in result
        ]
        return {"data": schema_data, "pagination": {}}

    async def list_job_requirements_by_company(
        self,
        company_id: UUID,
        status: Optional[JobRequirementStatus] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        search: Optional[str] = None,
        order_by: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
        user_id: Optional[UUID] = None,
        workspace_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """List job requirements for a specific company."""

        # Ensure the company exists
        company = await self.company_repo.get_by_id(company_id, workspace_id)
        if not company:
            raise CompanyNotFoundException(company_id=company_id)

        # Get job requirements by company
        job_requirements = await self.job_requirement_repo.get_by_company_id(
            company_id=company_id,
            status=status,
            workspace_id=workspace_id
        )

        # Apply pagination manually since get_by_company_id doesn't support it
        total_count = len(job_requirements)
        start_idx = skip
        end_idx = min(start_idx + limit, total_count)
        paginated_data = job_requirements[start_idx:end_idx]

        # Convert to schema objects
        schema_data = [
            JobRequirementReadSchema.model_validate(job_req) for job_req in paginated_data
        ]

        pagination = {
            "total_count": total_count,
            "offset": skip,
            "limit": limit,
            "total_pages": (total_count + limit - 1) // limit if limit > 0 else 1,
        }

        return {"data": schema_data, "pagination": pagination}

    async def update_job_requirement(
        self,
        job_requirement_id: UUID,
        payload: JobRequirementUpdateSchema,
        user_id: UUID,
        workspace_id: UUID,
    ) -> JobRequirementReadSchema:
        """Update a job requirement."""
        existing_job_req = await self.job_requirement_repo.get_by_id(
            job_requirement_id=job_requirement_id, workspace_id=workspace_id
        )
        if not existing_job_req:
            raise JobRequirementNotFoundException(job_requirement_id=job_requirement_id)

        payload_dict = payload.model_dump(exclude_unset=True)

        job_requirement = await self.job_requirement_repo.update(
            job_requirement_id=job_requirement_id,
            job_requirement_data=payload_dict,
            user_id=user_id,
            workspace_id=workspace_id,
        )

        log_user_activity(
            f"Job requirement updated: {job_requirement.title}",
            action_type="job_requirement_update"
        )
        return JobRequirementReadSchema.model_validate(job_requirement)

    async def update_job_requirement_status(
        self,
        job_requirement_id: UUID,
        status: JobRequirementStatus,
        user_id: UUID,
        workspace_id: UUID,
    ) -> JobRequirementReadSchema:
        """Update only the status of a job requirement."""
        job_requirement = await self.job_requirement_repo.update_status(
            job_requirement_id=job_requirement_id,
            status=status.value,
            user_id=user_id,
            workspace_id=workspace_id,
        )

        log_central(
            f"Job requirement {job_requirement_id} status updated to {status.value}",
            level="info",
        )

        return JobRequirementReadSchema.model_validate(job_requirement)

    async def delete_job_requirement(
        self, job_requirement_id: UUID, user_id: UUID, workspace_id: UUID
    ) -> None:
        """Delete a job requirement."""
        deleted = await self.job_requirement_repo.delete(
            job_requirement_id=job_requirement_id,
            user_id=user_id,
            workspace_id=workspace_id
        )

        if not deleted:
            raise JobRequirementNotFoundException(job_requirement_id=job_requirement_id)

        log_user_activity(
            f"Job requirement deleted: {job_requirement_id}",
            action_type="job_requirement_delete"
        )
