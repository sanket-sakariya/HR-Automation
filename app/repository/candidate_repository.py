from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app.config.constants import DatabaseErrorMessages
from app.model.candidate_model import CandidateModel
from app.repository.baseapp_repository import BaseAppRepository

from app.exception.candidate_management_exception import (
    CandidateNotFoundException,
    CandidateAlreadyExistsException,
    CandidateCreationException,
    CandidateUpdateException,
    CandidateDeletionException,
    DuplicateApplicationException,
    InternalServerErrorException,
)


class CandidateRepository(BaseAppRepository[CandidateModel]):
    """Candidate repository for candidate management operations."""

    def __init__(self, db):
        super().__init__(db=db, model=CandidateModel)

    async def insert(
        self,
        candidate_data: Dict[str, Any],
    ) -> CandidateModel:
        """Insert a new candidate (async). Prevents duplicate applications for same job."""
        try:
            # Check if candidate has already applied to this job
            candidate_id = candidate_data.get("candidate_id")
            job_requirement_id = candidate_data.get("job_requirement_id")

            existing_application = await self.get_by_candidate_and_job(candidate_id, job_requirement_id)
            if existing_application:
                raise DuplicateApplicationException(candidate_id, job_requirement_id)

            candidate = CandidateModel(**candidate_data)

            self.db.add(candidate)
            await self.db.commit()
            await self.db.refresh(candidate)

            return candidate
        except DuplicateApplicationException:
            raise
        except IntegrityError as e:
            # Handle database-level unique constraint violation
            if "unique_candidate_job" in str(e):
                raise DuplicateApplicationException(candidate_id, job_requirement_id)
            raise CandidateCreationException(
                message=f"Database constraint violation: {str(e)}"
            ) from e
        except SQLAlchemyError as e:
            raise CandidateCreationException(
                message=f"{DatabaseErrorMessages.GENERAL_CREATION_ERROR}: {str(e)}"
            ) from e

    async def get_by_id(self, candidate_id: UUID) -> Optional[CandidateModel]:
        """Get a candidate by ID (async)."""
        try:
            query = select(CandidateModel).where(CandidateModel.candidate_id == candidate_id)

            query = query.limit(1)

            result = await self.db.execute(query)
            candidate = result.scalar_one_or_none()

            # Return None if candidate is deleted
            if candidate and candidate.status == "deleted":
                raise CandidateNotFoundException(candidate_id=candidate_id)

            return candidate
        except SQLAlchemyError as e:
            raise InternalServerErrorException(
                message=f"{DatabaseErrorMessages.GENERAL_RETRIEVAL_ERROR}: {str(e)}"
            ) from e

    async def get_by_email(self, email: str) -> Optional[CandidateModel]:
        """Get a candidate by email (async)."""
        try:
            query = select(CandidateModel).where(
                and_(
                    CandidateModel.email == email,
                    CandidateModel.status != "deleted"
                )
            )

            query = query.limit(1)

            result = await self.db.execute(query)
            candidate = result.scalar_one_or_none()

            return candidate
        except SQLAlchemyError as e:
            raise InternalServerErrorException(
                message=f"{DatabaseErrorMessages.GENERAL_RETRIEVAL_ERROR}: {str(e)}"
            ) from e

    async def get_by_candidate_and_job(
        self, candidate_id: UUID, job_requirement_id: UUID
    ) -> Optional[CandidateModel]:
        """Get candidate application by candidate and job combination (async)."""
        try:
            query = select(CandidateModel).where(
                and_(
                    CandidateModel.candidate_id == candidate_id,
                    CandidateModel.job_requirement_id == job_requirement_id,
                    CandidateModel.status != "deleted"
                )
            )

            query = query.limit(1)

            result = await self.db.execute(query)
            candidate = result.scalar_one_or_none()

            return candidate
        except SQLAlchemyError as e:
            raise InternalServerErrorException(
                message=f"{DatabaseErrorMessages.GENERAL_RETRIEVAL_ERROR}: {str(e)}"
            ) from e

    async def update(
        self,
        candidate_id: UUID,
        candidate_data: Dict[str, Any],
    ) -> CandidateModel:
        """Update an existing candidate (async)."""
        try:
            candidate = await self.get_by_id(candidate_id)
            if not candidate:
                raise CandidateNotFoundException(candidate_id=candidate_id)

            # Note: No email uniqueness check since candidates can have multiple records

            for key, value in candidate_data.items():
                setattr(candidate, key, value)

            await self.db.commit()
            await self.db.refresh(candidate)

            return candidate
        except CandidateNotFoundException:
            raise
        except SQLAlchemyError as e:
            raise CandidateUpdateException(
                candidate_id=candidate_id,
                message=f"{DatabaseErrorMessages.GENERAL_UPDATE_ERROR}: {str(e)}"
            ) from e

    async def update_status(
        self,
        candidate_id: UUID,
        status: str,
    ) -> CandidateModel:
        """
        Update only the status of a candidate (async).
        Only works if current status is not 'deleted'.
        """
        try:
            candidate = await self.get_by_id(candidate_id)
            if not candidate:
                raise CandidateNotFoundException(candidate_id=candidate_id)

            candidate.status = status

            await self.db.commit()
            await self.db.refresh(candidate)
            return candidate
        except CandidateNotFoundException:
            raise
        except SQLAlchemyError as e:
            raise CandidateUpdateException(
                candidate_id=candidate_id,
                message=f"{DatabaseErrorMessages.GENERAL_STATUS_UPDATE_ERROR}: {str(e)}"
            ) from e

    async def update_is_active(
        self,
        candidate_id: UUID,
        is_active: bool,
    ) -> CandidateModel:
        """Update only the is_active flag of a candidate (async)."""
        try:
            candidate = await self.get_by_id(candidate_id)
            if not candidate:
                raise CandidateNotFoundException(candidate_id=candidate_id)

            candidate.is_active = is_active
            candidate.status = "active" if is_active else "inactive"

            await self.db.commit()
            await self.db.refresh(candidate)
            return candidate
        except CandidateNotFoundException:
            raise
        except SQLAlchemyError as e:
            raise CandidateUpdateException(
                candidate_id=candidate_id,
                message=f"{DatabaseErrorMessages.GENERAL_ACTIVE_UPDATE_ERROR}: {str(e)}"
            ) from e

    async def delete(
        self, candidate_id: UUID
    ) -> bool:
        """Soft delete a candidate (update status & is_active) (async)."""
        try:
            candidate = await self.get_by_id(candidate_id)
            if not candidate:
                raise CandidateNotFoundException(candidate_id=candidate_id)

            # mark as deleted (soft delete)
            candidate.deleted_at = datetime.now(timezone.utc)
            candidate.status = "deleted"
            candidate.is_active = False

            # persist changes
            await self.db.commit()
            await self.db.refresh(candidate)

            return True
        except CandidateNotFoundException:
            raise
        except SQLAlchemyError as e:
            raise CandidateDeletionException(candidate_id=candidate_id) from e

    async def get_all(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
        search: Optional[str] = None,
        order_by: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Get all candidates with dynamic filters + direct search + ordering + pagination.
        Uses the base repository's get_all method.
        """

        return await super().get_all(
            filters=filters,
            search=search,
            order_by=order_by,
            skip=skip,
            limit=limit
        )
