from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.exc import SQLAlchemyError

from app.config.constants import DatabaseErrorMessages
from app.model.job_requirement_model import JobRequirementModel
from app.repository.baseapp_repository import BaseAppRepository

from app.exception.company_management_exception import (
    JobRequirementNotFoundException,
    JobRequirementCreationException,
    JobRequirementUpdateException,
    JobRequirementDeletionException,
    InternalServerErrorException,
)


class JobRequirementRepository(BaseAppRepository[JobRequirementModel]):
    """Job requirement repository for job requirement management operations."""

    def __init__(self, db):
        super().__init__(db=db, model=JobRequirementModel)

    async def insert(
        self,
        job_requirement_data: Dict[str, Any],
        user_id: UUID = None,
        workspace_id: UUID = None,
    ) -> JobRequirementModel:
        """Insert a new job requirement (async). user_id optional."""
        try:
            job_requirement = JobRequirementModel(**job_requirement_data)
            if user_id is not None:
                job_requirement.created_by = user_id
            if workspace_id is not None:
                job_requirement.workspace_id = workspace_id

            self.db.add(job_requirement)
            await self.db.commit()
            await self.db.refresh(job_requirement)

            return job_requirement
        except SQLAlchemyError as e:
            raise JobRequirementCreationException(
                message=f"{DatabaseErrorMessages.JOB_REQUIREMENT_CREATION_ERROR}: {str(e)}"
            ) from e

    async def get_by_id(self, job_requirement_id: UUID, workspace_id: UUID = None) -> Optional[JobRequirementModel]:
        """Get a job requirement by ID and workspace (async)."""
        try:
            query = select(JobRequirementModel).where(JobRequirementModel.job_requirement_id == job_requirement_id)

            if workspace_id is not None:
                query = query.where(JobRequirementModel.workspace_id == workspace_id)

            query = query.limit(1)

            result = await self.db.execute(query)
            job_requirement = result.scalar_one_or_none()

            # Return None if job requirement is deleted
            if job_requirement and job_requirement.status == "deleted":
                raise JobRequirementNotFoundException(job_requirement_id=job_requirement_id)

            return job_requirement
        except SQLAlchemyError as e:
            raise InternalServerErrorException(
                message=f"{DatabaseErrorMessages.JOB_REQUIREMENT_RETRIEVAL_ERROR}: {str(e)}"
            ) from e

    async def get_by_company_id(
        self,
        company_id: UUID,
        status: Optional[str] = None,
        workspace_id: UUID = None
    ) -> List[JobRequirementModel]:
        """Get job requirements by company ID (async)."""
        try:
            query = select(JobRequirementModel).where(
                and_(
                    JobRequirementModel.company_id == company_id,
                    JobRequirementModel.status != "deleted"
                )
            )

            if workspace_id is not None:
                query = query.where(JobRequirementModel.workspace_id == workspace_id)

            if status is not None:
                query = query.where(JobRequirementModel.status == status)

            result = await self.db.execute(query)
            job_requirements = result.scalars().all()

            return list(job_requirements)
        except SQLAlchemyError as e:
            raise InternalServerErrorException(
                message=f"{DatabaseErrorMessages.JOB_REQUIREMENT_RETRIEVAL_ERROR}: {str(e)}"
            ) from e

    async def update(
        self,
        job_requirement_id: UUID,
        job_requirement_data: Dict[str, Any],
        user_id: UUID = None,
        workspace_id: UUID = None,
    ) -> JobRequirementModel:
        """Update an existing job requirement (async)."""
        try:
            job_requirement = await self.get_by_id(job_requirement_id, workspace_id=workspace_id)
            if not job_requirement:
                raise JobRequirementNotFoundException(job_requirement_id=job_requirement_id)

            for key, value in job_requirement_data.items():
                setattr(job_requirement, key, value)

            if user_id is not None:
                job_requirement.updated_by = user_id

            await self.db.commit()
            await self.db.refresh(job_requirement)

            return job_requirement
        except JobRequirementNotFoundException:
            raise
        except SQLAlchemyError as e:
            raise JobRequirementUpdateException(
                job_requirement_id=job_requirement_id,
                message=f"{DatabaseErrorMessages.JOB_REQUIREMENT_UPDATE_ERROR}: {str(e)}"
            ) from e

    async def update_status(
        self,
        job_requirement_id: UUID,
        status: str,
        error_message: str = None,
        error_user_message: str = None,
        user_id: UUID = None,
        workspace_id: UUID = None,
    ) -> JobRequirementModel:
        """
        Update only the status of a job requirement (async).
        Only works if current status is not 'deleted'.
        """
        try:
            job_requirement = await self.get_by_id(job_requirement_id, workspace_id=workspace_id)
            if not job_requirement:
                raise JobRequirementNotFoundException(job_requirement_id=job_requirement_id)

            job_requirement.status = status
            job_requirement.error_message = error_message
            job_requirement.error_user_message = error_user_message
            if user_id is not None:
                job_requirement.updated_by = user_id

            await self.db.commit()
            await self.db.refresh(job_requirement)
            return job_requirement
        except JobRequirementNotFoundException:
            raise
        except SQLAlchemyError as e:
            raise JobRequirementUpdateException(
                job_requirement_id=job_requirement_id,
                message=f"{DatabaseErrorMessages.JOB_REQUIREMENT_STATUS_UPDATE_ERROR}: {str(e)}"
            ) from e

    async def update_is_active(
        self,
        job_requirement_id: UUID,
        is_active: bool,
        user_id: UUID = None,
        workspace_id: UUID = None,
    ) -> JobRequirementModel:
        """Update only the is_active flag of a job requirement (async)."""
        try:
            job_requirement = await self.get_by_id(job_requirement_id, workspace_id=workspace_id)
            if not job_requirement:
                raise JobRequirementNotFoundException(job_requirement_id=job_requirement_id)

            job_requirement.is_active = is_active
            if user_id is not None:
                job_requirement.updated_by = user_id

            await self.db.commit()
            await self.db.refresh(job_requirement)
            return job_requirement
        except JobRequirementNotFoundException:
            raise
        except SQLAlchemyError as e:
            raise JobRequirementUpdateException(
                job_requirement_id=job_requirement_id,
                message=f"{DatabaseErrorMessages.JOB_REQUIREMENT_ACTIVE_UPDATE_ERROR}: {str(e)}"
            ) from e

    async def delete(
        self, job_requirement_id: UUID, user_id: UUID = None, workspace_id: UUID = None
    ) -> bool:
        """Soft delete a job requirement (update status & is_active) (async)."""
        try:
            job_requirement = await self.get_by_id(job_requirement_id, workspace_id=workspace_id)
            if not job_requirement:
                raise JobRequirementNotFoundException(job_requirement_id=job_requirement_id)

            # mark as deleted (soft delete)
            job_requirement.deleted_at = datetime.now(timezone.utc)
            job_requirement.deleted_by = user_id
            job_requirement.status = "deleted"
            job_requirement.is_active = False
            if user_id is not None:
                job_requirement.updated_by = user_id

            # persist changes
            await self.db.commit()
            await self.db.refresh(job_requirement)

            return True
        except JobRequirementNotFoundException:
            raise
        except SQLAlchemyError as e:
            raise JobRequirementDeletionException(job_requirement_id=job_requirement_id) from e

    async def get_all(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
        search: Optional[str] = None,
        order_by: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
        user_id: Optional[UUID] = None,
        workspace_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """
        Get all job requirements with dynamic filters + direct search + ordering + pagination.
        Uses the base repository's get_all method.
        """

        return await super().get_all(
            filters=filters,
            search=search,
            order_by=order_by,
            skip=skip,
            limit=limit,
            user_id=user_id,
            workspace_id=workspace_id,
        )
