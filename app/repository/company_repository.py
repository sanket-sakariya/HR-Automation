from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.exc import SQLAlchemyError

from app.config.constants import DatabaseErrorMessages
from app.model.company_model import CompanyModel
from app.repository.baseapp_repository import BaseAppRepository

from app.exception.company_management_exception import (
    CompanyNotFoundException,
    CompanyAlreadyExistsException,
    CompanyCreationException,
    CompanyUpdateException,
    CompanyDeletionException,
    InternalServerErrorException,
)


class CompanyRepository(BaseAppRepository[CompanyModel]):
    """Company repository for company management operations."""

    def __init__(self, db):
        super().__init__(db=db, model=CompanyModel)

    async def insert(
        self,
        company_data: Dict[str, Any],
        user_id: UUID = None,
        workspace_id: UUID = None,
    ) -> CompanyModel:
        """Insert a new company (async). user_id optional."""
        try:
            # Check if company with same email already exists in this workspace
            existing_company = await self.get_by_email(company_data.get("email"), workspace_id)
            if existing_company:
                raise CompanyAlreadyExistsException(company_data.get("email"))

            company = CompanyModel(**company_data)
            if user_id is not None:
                company.created_by = user_id
            if workspace_id is not None:
                company.workspace_id = workspace_id

            self.db.add(company)
            await self.db.commit()
            await self.db.refresh(company)

            return company
        except CompanyAlreadyExistsException:
            raise
        except SQLAlchemyError as e:
            raise CompanyCreationException(
                message=f"{DatabaseErrorMessages.COMPANY_CREATION_ERROR}: {str(e)}"
            ) from e

    async def get_by_id(self, company_id: UUID, workspace_id: UUID = None) -> Optional[CompanyModel]:
        """Get a company by ID and workspace (async)."""
        try:
            query = select(CompanyModel).where(CompanyModel.company_id == company_id)

            if workspace_id is not None:
                query = query.where(CompanyModel.workspace_id == workspace_id)

            query = query.limit(1)

            result = await self.db.execute(query)
            company = result.scalar_one_or_none()

            # Return None if company is deleted
            if company and company.status == "deleted":
                raise CompanyNotFoundException(company_id=company_id)

            return company
        except SQLAlchemyError as e:
            raise InternalServerErrorException(
                message=f"{DatabaseErrorMessages.COMPANY_RETRIEVAL_ERROR}: {str(e)}"
            ) from e

    async def get_by_email(self, email: str, workspace_id: UUID = None) -> Optional[CompanyModel]:
        """Get a company by email (async)."""
        try:
            query = select(CompanyModel).where(
                and_(
                    CompanyModel.email == email,
                    CompanyModel.status != "deleted"
                )
            )

            if workspace_id is not None:
                query = query.where(CompanyModel.workspace_id == workspace_id)

            query = query.limit(1)

            result = await self.db.execute(query)
            company = result.scalar_one_or_none()

            return company
        except SQLAlchemyError as e:
            raise InternalServerErrorException(
                message=f"{DatabaseErrorMessages.COMPANY_RETRIEVAL_ERROR}: {str(e)}"
            ) from e

    async def update(
        self,
        company_id: UUID,
        company_data: Dict[str, Any],
        user_id: UUID = None,
        workspace_id: UUID = None,
    ) -> CompanyModel:
        """Update an existing company (async)."""
        try:
            company = await self.get_by_id(company_id, workspace_id=workspace_id)
            if not company:
                raise CompanyNotFoundException(company_id=company_id)

            # Check if email is being updated and if it conflicts
            if "email" in company_data and company_data["email"] != company.email:
                existing_company = await self.get_by_email(company_data["email"], workspace_id)
                if existing_company and existing_company.company_id != company_id:
                    raise CompanyAlreadyExistsException(company_data["email"])

            for key, value in company_data.items():
                setattr(company, key, value)

            if user_id is not None:
                company.updated_by = user_id

            await self.db.commit()
            await self.db.refresh(company)

            return company
        except (CompanyNotFoundException, CompanyAlreadyExistsException):
            raise
        except SQLAlchemyError as e:
            raise CompanyUpdateException(
                company_id=company_id,
                message=f"{DatabaseErrorMessages.COMPANY_UPDATE_ERROR}: {str(e)}"
            ) from e

    async def update_status(
        self,
        company_id: UUID,
        status: str,
        error_message: str = None,
        error_user_message: str = None,
        user_id: UUID = None,
        workspace_id: UUID = None,
    ) -> CompanyModel:
        """
        Update only the status of a company (async).
        Only works if current status is not 'deleted'.
        """
        try:
            company = await self.get_by_id(company_id, workspace_id=workspace_id)
            if not company:
                raise CompanyNotFoundException(company_id=company_id)

            company.status = status
            company.error_message = error_message
            company.error_user_message = error_user_message
            if user_id is not None:
                company.updated_by = user_id

            await self.db.commit()
            await self.db.refresh(company)
            return company
        except CompanyNotFoundException:
            raise
        except SQLAlchemyError as e:
            raise CompanyUpdateException(
                company_id=company_id,
                message=f"{DatabaseErrorMessages.COMPANY_STATUS_UPDATE_ERROR}: {str(e)}"
            ) from e

    async def update_is_active(
        self,
        company_id: UUID,
        is_active: bool,
        user_id: UUID = None,
        workspace_id: UUID = None,
    ) -> CompanyModel:
        """Update only the is_active flag of a company (async)."""
        try:
            company = await self.get_by_id(company_id, workspace_id=workspace_id)
            if not company:
                raise CompanyNotFoundException(company_id=company_id)

            company.is_active = is_active
            if user_id is not None:
                company.updated_by = user_id

            await self.db.commit()
            await self.db.refresh(company)
            return company
        except CompanyNotFoundException:
            raise
        except SQLAlchemyError as e:
            raise CompanyUpdateException(
                company_id=company_id,
                message=f"{DatabaseErrorMessages.COMPANY_ACTIVE_UPDATE_ERROR}: {str(e)}"
            ) from e

    async def delete(
        self, company_id: UUID, user_id: UUID = None, workspace_id: UUID = None
    ) -> bool:
        """Soft delete a company (update status & is_active) (async)."""
        try:
            company = await self.get_by_id(company_id, workspace_id=workspace_id)
            if not company:
                raise CompanyNotFoundException(company_id=company_id)

            # mark as deleted (soft delete)
            company.deleted_at = datetime.now(timezone.utc)
            company.deleted_by = user_id
            company.status = "deleted"
            company.is_active = False
            if user_id is not None:
                company.updated_by = user_id

            # persist changes
            await self.db.commit()
            await self.db.refresh(company)

            return True
        except CompanyNotFoundException:
            raise
        except SQLAlchemyError as e:
            raise CompanyDeletionException(company_id=company_id) from e

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
        Get all companies with dynamic filters + direct search + ordering + pagination.
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
