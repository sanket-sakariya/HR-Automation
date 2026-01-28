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

    async def get_by_email_and_job_requirement(self, email: str, job_requirement_id: str) -> Optional[CandidateModel]:
        """Get a candidate by email and job_requirement_id (async)."""
        try:
            query = select(CandidateModel).where(
                and_(
                    CandidateModel.email == email,
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

    async def update_aptitude_test_result(
        self,
        email: str,
        job_requirement_id: UUID,
        aptitude_test: bool,
        aptitude_test_result: str,  # 'pass' or 'fail'
    ) -> Optional[CandidateModel]:
        """
        Update aptitude test fields for a candidate based on email and job requirement.
        Sets aptitude_test to True and aptitude_test_result to 'pass' or 'fail'.
        """
        try:
            candidate = await self.get_by_email_and_job_requirement(email, str(job_requirement_id))
            if not candidate:
                return None

            candidate.aptitude_test = aptitude_test
            candidate.aptitude_test_result = aptitude_test_result

            await self.db.commit()
            await self.db.refresh(candidate)
            return candidate
        except SQLAlchemyError as e:
            raise CandidateUpdateException(
                candidate_id=candidate.candidate_id if candidate else None,
                message=f"Failed to update aptitude test result: {str(e)}"
            ) from e

    async def bulk_update_aptitude_test_results(
        self,
        job_requirement_id: UUID,
        passed_emails: List[str],
        failed_emails: List[str],
    ) -> Dict[str, Any]:
        """
        Bulk update aptitude test results for multiple candidates.
        Candidates in passed_emails get aptitude_test=True and aptitude_test_result='pass'.
        Candidates in failed_emails get aptitude_test=True and aptitude_test_result='fail'.
        """
        updated_passed = []
        updated_failed = []
        not_found = []

        # Update passed candidates
        for email in passed_emails:
            candidate = await self.update_aptitude_test_result(
                email=email,
                job_requirement_id=job_requirement_id,
                aptitude_test=True,
                aptitude_test_result="pass"
            )
            if candidate:
                updated_passed.append(email)
            else:
                not_found.append(email)

        # Update failed candidates
        for email in failed_emails:
            candidate = await self.update_aptitude_test_result(
                email=email,
                job_requirement_id=job_requirement_id,
                aptitude_test=True,
                aptitude_test_result="fail"
            )
            if candidate:
                updated_failed.append(email)
            else:
                not_found.append(email)

        return {
            "updated_passed": updated_passed,
            "updated_failed": updated_failed,
            "not_found": not_found
        }

    async def get_candidates_by_job_with_resume_score(
        self,
        job_requirement_id: UUID,
    ) -> List[CandidateModel]:
        """
        Get all candidates for a job requirement sorted by resume score (descending).
        Only returns candidates with a resume score.
        """
        try:
            query = select(CandidateModel).where(
                and_(
                    CandidateModel.job_requirement_id == job_requirement_id,
                    CandidateModel.status != "deleted",
                    CandidateModel.candidate_resume_score.isnot(None)
                )
            ).order_by(CandidateModel.candidate_resume_score.desc())

            result = await self.db.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise InternalServerErrorException(
                message=f"Failed to get candidates by job with resume score: {str(e)}"
            ) from e

    async def update_resume_selected(
        self,
        candidate_id: UUID,
        resume_selected: bool,
    ) -> Optional[CandidateModel]:
        """Update resume_selected field for a candidate."""
        try:
            candidate = await self.get_by_id(candidate_id)
            if not candidate:
                return None

            candidate.resume_selected = resume_selected

            await self.db.commit()
            await self.db.refresh(candidate)
            return candidate
        except SQLAlchemyError as e:
            raise CandidateUpdateException(
                candidate_id=candidate_id,
                message=f"Failed to update resume_selected: {str(e)}"
            ) from e

    async def bulk_update_resume_selected(
        self,
        job_requirement_id: UUID,
        top_n: int,
    ) -> Dict[str, Any]:
        """
        Select top N candidates based on resume score for a job requirement.
        Sets resume_selected=True for top N, False for others.
        """
        # Get all candidates with resume score sorted by score
        candidates = await self.get_candidates_by_job_with_resume_score(job_requirement_id)
        
        if not candidates:
            return {
                "total_candidates": 0,
                "selected_count": 0,
                "rejected_count": 0,
                "selected_candidates": [],
                "rejected_candidates": []
            }

        selected_candidates = []
        rejected_candidates = []

        for idx, candidate in enumerate(candidates):
            if idx < top_n:
                # Top N candidates - selected
                candidate.resume_selected = True
                selected_candidates.append({
                    "candidate_id": str(candidate.candidate_id),
                    "email": candidate.email,
                    "name": f"{candidate.first_name} {candidate.last_name}",
                    "resume_score": float(candidate.candidate_resume_score) if candidate.candidate_resume_score else None,
                    "rank": idx + 1
                })
            else:
                # Rest - not selected
                candidate.resume_selected = False
                rejected_candidates.append({
                    "candidate_id": str(candidate.candidate_id),
                    "email": candidate.email,
                    "name": f"{candidate.first_name} {candidate.last_name}",
                    "resume_score": float(candidate.candidate_resume_score) if candidate.candidate_resume_score else None,
                    "rank": idx + 1
                })

        await self.db.commit()

        return {
            "total_candidates": len(candidates),
            "selected_count": len(selected_candidates),
            "rejected_count": len(rejected_candidates),
            "selected_candidates": selected_candidates,
            "rejected_candidates": rejected_candidates
        }
