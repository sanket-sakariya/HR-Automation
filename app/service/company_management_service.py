from __future__ import annotations

from typing import Optional, Dict, Any, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.logger_config import log_user_activity, log_central
from app.config.constants import LogMessages

from app.schema.company_management_schema import (
    CompanyCreateSchema,
    CompanyUpdateSchema,
    CompanyReadSchema,
    JobRequirementCreateSchema,
    JobRequirementUpdateSchema,
    JobRequirementReadSchema,
    JobRequirementStatus,
)

from app.exception.company_management_exception import (
    CompanyNotFoundException,
    JobRequirementNotFoundException,
)

from app.service.baseapp_service import BaseAppService
from app.repository.company_repository import CompanyRepository
from app.repository.job_requirement_repository import JobRequirementRepository


class CompanyManagementService(BaseAppService):
    """Company management service."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db)
        self.company_repo = CompanyRepository(db=db)
        self.job_requirement_repo = JobRequirementRepository(db=db)

    # ==================== COMPANY OPERATIONS ====================

    async def create_company(
        self, payload: CompanyCreateSchema, user_id: UUID, workspace_id: UUID
    ) -> CompanyReadSchema:
        """Create a new company."""

        company_data = payload.model_dump()

        # Convert AnyHttpUrl fields to strings
        if company_data.get("website"):
            company_data["website"] = str(company_data["website"])
        if company_data.get("logo"):
            company_data["logo"] = str(company_data["logo"])

        # Remove password from data as it's handled separately (e.g., authentication service)
        company_data.pop("password", None)

        company = await self.company_repo.insert(
            company_data=company_data, user_id=user_id, workspace_id=workspace_id
        )

        log_user_activity(
            f"Company created: {company.company_name}",
            action_type="company_create",
            level="info",
        )

        return CompanyReadSchema.model_validate(company)

    async def get_company(
        self, company_id: UUID, user_id: UUID, workspace_id: UUID
    ) -> CompanyReadSchema:
        """Get a company by ID."""
        company = await self.company_repo.get_by_id(
            company_id=company_id, workspace_id=workspace_id
        )
        if not company:
            raise CompanyNotFoundException(company_id=company_id)
        return CompanyReadSchema.model_validate(company)

    async def list_companies(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
        search: Optional[str] = None,
        order_by: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
        user_id: Optional[UUID] = None,
        workspace_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """List all companies."""

        result = await self.company_repo.get_all(
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
                CompanyReadSchema.model_validate(company) for company in data
            ]
            return {"data": schema_data, "pagination": pagination}

        # Fallback for non-dict results
        schema_data = [
            CompanyReadSchema.model_validate(company) for company in result
        ]
        return {"data": schema_data, "pagination": {}}

    async def update_company(
        self,
        company_id: UUID,
        payload: CompanyUpdateSchema,
        user_id: UUID,
        workspace_id: UUID,
    ) -> CompanyReadSchema:
        """Update a company."""
        existing_company = await self.company_repo.get_by_id(
            company_id=company_id, workspace_id=workspace_id
        )
        if not existing_company:
            raise CompanyNotFoundException(company_id=company_id)

        payload_dict = payload.model_dump(exclude_unset=True)

        # Convert AnyHttpUrl fields to strings
        if payload_dict.get("website"):
            payload_dict["website"] = str(payload_dict["website"])
        if payload_dict.get("logo"):
            payload_dict["logo"] = str(payload_dict["logo"])

        company = await self.company_repo.update(
            company_id=company_id,
            company_data=payload_dict,
            user_id=user_id,
            workspace_id=workspace_id,
        )

        log_user_activity(
            f"Company updated: {company.company_name}",
            action_type="company_update"
        )
        return CompanyReadSchema.model_validate(company)

    async def delete_company(self, company_id: UUID, user_id: UUID, workspace_id: UUID) -> None:
        """Delete a company."""
        deleted = await self.company_repo.delete(
            company_id=company_id, user_id=user_id, workspace_id=workspace_id
        )

        if not deleted:
            raise CompanyNotFoundException(company_id=company_id)

        log_user_activity(
            f"Company deleted: {company_id}",
            action_type="company_delete"
        )

    # ==================== JOB REQUIREMENT OPERATIONS ====================

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
