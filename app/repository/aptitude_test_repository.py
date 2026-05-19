"""Aptitude Test Repository."""

from __future__ import annotations
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.aptitude_test_model import AptitudeTestModel
from app.model.aptitude_question_model import AptitudeQuestionModel
from app.model.aptitude_test_attempt_model import AptitudeTestAttemptModel


class AptitudeTestRepository:
    """Repository for aptitude test operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_test(self, test_data: dict) -> AptitudeTestModel:
        """Create a new aptitude test."""
        test = AptitudeTestModel(**test_data)
        self.db.add(test)
        await self.db.commit()
        await self.db.refresh(test)
        return test

    async def create_question(self, question_data: dict) -> AptitudeQuestionModel:
        """Create a new question."""
        question = AptitudeQuestionModel(**question_data)
        self.db.add(question)
        await self.db.commit()
        await self.db.refresh(question)
        return question

    async def bulk_create_questions(self, questions_data: List[dict]) -> List[AptitudeQuestionModel]:
        """Create multiple questions at once."""
        questions = [AptitudeQuestionModel(**q_data) for q_data in questions_data]
        self.db.add_all(questions)
        await self.db.commit()
        for question in questions:
            await self.db.refresh(question)
        return questions

    async def get_test_by_id(self, test_id: UUID) -> Optional[AptitudeTestModel]:
        """Get test by ID."""
        query = select(AptitudeTestModel).where(AptitudeTestModel.aptitude_test_id == test_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_test_by_job_id(self, job_requirement_id: UUID) -> Optional[AptitudeTestModel]:
        """Get test by job requirement ID."""
        query = select(AptitudeTestModel).where(
            AptitudeTestModel.job_requirement_id == job_requirement_id,
            AptitudeTestModel.is_active == True
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_questions_by_test_id(self, test_id: UUID) -> List[AptitudeQuestionModel]:
        """Get all questions for a test."""
        query = select(AptitudeQuestionModel).where(
            AptitudeQuestionModel.aptitude_test_id == test_id
        ).order_by(AptitudeQuestionModel.question_number)
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def create_attempt(self, attempt_data: dict) -> AptitudeTestAttemptModel:
        """Create a new test attempt."""
        attempt = AptitudeTestAttemptModel(**attempt_data)
        self.db.add(attempt)
        await self.db.commit()
        await self.db.refresh(attempt)
        return attempt

    async def get_attempt_by_id(self, attempt_id: UUID) -> Optional[AptitudeTestAttemptModel]:
        """Get attempt by ID."""
        query = select(AptitudeTestAttemptModel).where(
            AptitudeTestAttemptModel.attempt_id == attempt_id
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_attempt(self, attempt_id: UUID, update_data: dict) -> AptitudeTestAttemptModel:
        """Update test attempt."""
        attempt = await self.get_attempt_by_id(attempt_id)
        if attempt:
            for key, value in update_data.items():
                setattr(attempt, key, value)
            await self.db.commit()
            await self.db.refresh(attempt)
        return attempt

    async def get_attempts_by_email(self, email: str, test_id: UUID) -> List[AptitudeTestAttemptModel]:
        """Get all attempts by email for a specific test."""
        query = select(AptitudeTestAttemptModel).where(
            AptitudeTestAttemptModel.candidate_email == email,
            AptitudeTestAttemptModel.aptitude_test_id == test_id
        ).order_by(AptitudeTestAttemptModel.created_at.desc())

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_attempt_by_email_and_test(self, email: str, test_id: UUID) -> Optional[AptitudeTestAttemptModel]:
        """Get the most recent attempt by email for a specific test."""
        query = select(AptitudeTestAttemptModel).where(
            AptitudeTestAttemptModel.candidate_email == email,
            AptitudeTestAttemptModel.aptitude_test_id == test_id
        ).order_by(AptitudeTestAttemptModel.created_at.desc()).limit(1)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_completed_attempts_by_job_and_test(
        self, 
        job_requirement_id: UUID, 
        aptitude_test_id: UUID
    ) -> List[AptitudeTestAttemptModel]:
        """
        Get all completed attempts for a specific job requirement and aptitude test,
        sorted by score in descending order (highest score first).
        """
        query = select(AptitudeTestAttemptModel).where(
            AptitudeTestAttemptModel.job_requirement_id == job_requirement_id,
            AptitudeTestAttemptModel.aptitude_test_id == aptitude_test_id,
            AptitudeTestAttemptModel.status == "completed",
            AptitudeTestAttemptModel.score.isnot(None)
        ).order_by(AptitudeTestAttemptModel.score.desc())

        result = await self.db.execute(query)
        return result.scalars().all()

    async def delete_attempts_by_email(
        self,
        email: str,
        aptitude_test_id: Optional[UUID] = None,
        job_requirement_id: Optional[UUID] = None,
    ) -> int:
        """
        Hard-delete aptitude test attempts for a candidate email.

        Used to allow a candidate to retake the aptitude test by clearing
        the previous attempt(s). Returns the number of rows removed.
        """
        stmt = delete(AptitudeTestAttemptModel).where(
            AptitudeTestAttemptModel.candidate_email == email
        )
        if aptitude_test_id is not None:
            stmt = stmt.where(AptitudeTestAttemptModel.aptitude_test_id == aptitude_test_id)
        if job_requirement_id is not None:
            stmt = stmt.where(AptitudeTestAttemptModel.job_requirement_id == job_requirement_id)

        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount or 0

