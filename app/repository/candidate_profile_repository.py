from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.exc import SQLAlchemyError

from app.config.constants import DatabaseErrorMessages
from app.model.candidate_profile_model import CandidateProfileModel
from app.repository.baseapp_repository import BaseAppRepository

from app.exception.candidate_management_exception import (
    CandidateProfileNotFoundException,
    CandidateProfileCreationException,
    CandidateProfileUpdateException,
    CandidateProfileDeletionException,
    InternalServerErrorException,
)


class CandidateProfileRepository(BaseAppRepository[CandidateProfileModel]):
    """Candidate profile repository for work experience and education operations."""

    def __init__(self, db):
        super().__init__(db=db, model=CandidateProfileModel)

    async def insert(
        self,
        profile_data: Dict[str, Any],
        user_id: UUID = None,
        workspace_id: UUID = None,
    ) -> CandidateProfileModel:
        """Insert a new candidate profile (async)."""
        try:
            profile = CandidateProfileModel(**profile_data)
            if user_id is not None:
                profile.created_by = user_id
            if workspace_id is not None:
                profile.workspace_id = workspace_id

            self.db.add(profile)
            await self.db.commit()
            await self.db.refresh(profile)

            return profile
        except SQLAlchemyError as e:
            raise CandidateProfileCreationException(
                message=f"{DatabaseErrorMessages.GENERAL_CREATION_ERROR}: {str(e)}"
            ) from e

    async def get_by_id(self, profile_id: UUID, workspace_id: UUID = None) -> Optional[CandidateProfileModel]:
        """Get a candidate profile by ID and workspace (async)."""
        try:
            query = select(CandidateProfileModel).where(CandidateProfileModel.candidate_profile_id == profile_id)

            if workspace_id is not None:
                query = query.where(CandidateProfileModel.workspace_id == workspace_id)

            query = query.limit(1)

            result = await self.db.execute(query)
            profile = result.scalar_one_or_none()

            # Return None if profile is deleted
            if profile and profile.status == "deleted":
                raise CandidateProfileNotFoundException(candidate_profile_id=profile_id)

            return profile
        except SQLAlchemyError as e:
            raise InternalServerErrorException(
                message=f"{DatabaseErrorMessages.GENERAL_RETRIEVAL_ERROR}: {str(e)}"
            ) from e

    async def get_by_candidate_id(
        self,
        candidate_id: UUID,
        profile_type: Optional[str] = None,
        workspace_id: UUID = None
    ) -> List[CandidateProfileModel]:
        """Get all profiles for a candidate, optionally filtered by type (async)."""
        try:
            query = select(CandidateProfileModel).where(
                and_(
                    CandidateProfileModel.candidate_id == candidate_id,
                    CandidateProfileModel.status != "deleted"
                )
            )

            if profile_type:
                query = query.where(CandidateProfileModel.profile_type == profile_type)

            if workspace_id is not None:
                query = query.where(CandidateProfileModel.workspace_id == workspace_id)

            result = await self.db.execute(query)
            profiles = result.scalars().all()

            return list(profiles)
        except SQLAlchemyError as e:
            raise InternalServerErrorException(
                message=f"{DatabaseErrorMessages.GENERAL_RETRIEVAL_ERROR}: {str(e)}"
            ) from e

    async def update(
        self,
        profile_id: UUID,
        profile_data: Dict[str, Any],
        user_id: UUID = None,
        workspace_id: UUID = None,
    ) -> CandidateProfileModel:
        """Update an existing candidate profile (async)."""
        try:
            profile = await self.get_by_id(profile_id, workspace_id=workspace_id)
            if not profile:
                raise CandidateProfileNotFoundException(candidate_profile_id=profile_id)

            for key, value in profile_data.items():
                setattr(profile, key, value)

            if user_id is not None:
                profile.updated_by = user_id

            await self.db.commit()
            await self.db.refresh(profile)

            return profile
        except CandidateProfileNotFoundException:
            raise
        except SQLAlchemyError as e:
            raise CandidateProfileUpdateException(
                candidate_profile_id=profile_id,
                message=f"{DatabaseErrorMessages.GENERAL_UPDATE_ERROR}: {str(e)}"
            ) from e

    async def update_status(
        self,
        profile_id: UUID,
        status: str,
        error_message: str = None,
        error_user_message: str = None,
        user_id: UUID = None,
        workspace_id: UUID = None,
    ) -> CandidateProfileModel:
        """
        Update only the status of a candidate profile (async).
        Only works if current status is not 'deleted'.
        """
        try:
            profile = await self.get_by_id(profile_id, workspace_id=workspace_id)
            if not profile:
                raise CandidateProfileNotFoundException(candidate_profile_id=profile_id)

            profile.status = status
            profile.error_message = error_message
            profile.error_user_message = error_user_message
            if user_id is not None:
                profile.updated_by = user_id

            await self.db.commit()
            await self.db.refresh(profile)
            return profile
        except CandidateProfileNotFoundException:
            raise
        except SQLAlchemyError as e:
            raise CandidateProfileUpdateException(
                candidate_profile_id=profile_id,
                message=f"{DatabaseErrorMessages.GENERAL_STATUS_UPDATE_ERROR}: {str(e)}"
            ) from e

    async def update_is_active(
        self,
        profile_id: UUID,
        is_active: bool,
        user_id: UUID = None,
        workspace_id: UUID = None,
    ) -> CandidateProfileModel:
        """Update only the is_active flag of a candidate profile (async)."""
        try:
            profile = await self.get_by_id(profile_id, workspace_id=workspace_id)
            if not profile:
                raise CandidateProfileNotFoundException(candidate_profile_id=profile_id)

            profile.is_active = is_active
            if user_id is not None:
                profile.updated_by = user_id

            await self.db.commit()
            await self.db.refresh(profile)
            return profile
        except CandidateProfileNotFoundException:
            raise
        except SQLAlchemyError as e:
            raise CandidateProfileUpdateException(
                candidate_profile_id=profile_id,
                message=f"{DatabaseErrorMessages.GENERAL_ACTIVE_UPDATE_ERROR}: {str(e)}"
            ) from e

    async def delete(
        self, profile_id: UUID, user_id: UUID = None, workspace_id: UUID = None
    ) -> bool:
        """Soft delete a candidate profile (update status & is_active) (async)."""
        try:
            profile = await self.get_by_id(profile_id, workspace_id=workspace_id)
            if not profile:
                raise CandidateProfileNotFoundException(candidate_profile_id=profile_id)

            # mark as deleted (soft delete)
            profile.deleted_at = datetime.now(timezone.utc)
            profile.deleted_by = user_id
            profile.status = "deleted"
            profile.is_active = False
            if user_id is not None:
                profile.updated_by = user_id

            # persist changes
            await self.db.commit()
            await self.db.refresh(profile)

            return True
        except CandidateProfileNotFoundException:
            raise
        except SQLAlchemyError as e:
            raise CandidateProfileDeletionException(candidate_profile_id=profile_id) from e

    async def delete_by_candidate_id(
        self, candidate_id: UUID, user_id: UUID = None, workspace_id: UUID = None
    ) -> bool:
        """Soft delete all profiles for a candidate (async)."""
        try:
            profiles = await self.get_by_candidate_id(candidate_id, workspace_id=workspace_id)

            for profile in profiles:
                profile.deleted_at = datetime.now(timezone.utc)
                profile.deleted_by = user_id
                profile.status = "deleted"
                profile.is_active = False
                if user_id is not None:
                    profile.updated_by = user_id

            # persist changes
            await self.db.commit()

            return True
        except SQLAlchemyError as e:
            raise InternalServerErrorException(
                message=f"{DatabaseErrorMessages.GENERAL_UPDATE_ERROR}: {str(e)}"
            ) from e

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
        Get all candidate profiles with dynamic filters + direct search + ordering + pagination.
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
