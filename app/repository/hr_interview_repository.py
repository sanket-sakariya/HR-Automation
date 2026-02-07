"""HR Interview Repository."""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.model.hr_interview_model import HRInterviewModel
from app.repository.baseapp_repository import BaseAppRepository


class HRInterviewRepository(BaseAppRepository[HRInterviewModel]):
    """Repository for HR interview operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=HRInterviewModel)
        self.db = db

    async def create_interview(self, interview_data: Dict[str, Any]) -> HRInterviewModel:
        """Create a new HR interview record."""
        interview = HRInterviewModel(**interview_data)
        self.db.add(interview)
        await self.db.commit()
        await self.db.refresh(interview)
        return interview

    async def get_by_id(self, hr_interview_id: UUID) -> Optional[HRInterviewModel]:
        """Get HR interview by ID."""
        query = select(HRInterviewModel).where(
            HRInterviewModel.hr_interview_id == hr_interview_id
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_session_id(self, session_id: str) -> Optional[HRInterviewModel]:
        """Get HR interview by session ID."""
        query = select(HRInterviewModel).where(
            HRInterviewModel.interview_session_id == session_id
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_candidate_and_job(
        self, 
        candidate_id: UUID, 
        job_requirement_id: UUID
    ) -> Optional[HRInterviewModel]:
        """Get HR interview by candidate and job requirement."""
        query = select(HRInterviewModel).where(
            and_(
                HRInterviewModel.candidate_id == candidate_id,
                HRInterviewModel.job_requirement_id == job_requirement_id,
                HRInterviewModel.status != "deleted"
            )
        ).order_by(desc(HRInterviewModel.created_at)).limit(1)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_pending_interview(
        self, 
        candidate_id: UUID, 
        job_requirement_id: UUID
    ) -> Optional[HRInterviewModel]:
        """Get pending or in-progress interview for a candidate."""
        query = select(HRInterviewModel).where(
            and_(
                HRInterviewModel.candidate_id == candidate_id,
                HRInterviewModel.job_requirement_id == job_requirement_id,
                HRInterviewModel.interview_status.in_(["pending", "in_progress"]),
                HRInterviewModel.status != "deleted"
            )
        ).order_by(desc(HRInterviewModel.created_at)).limit(1)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_interview(
        self, 
        hr_interview_id: UUID, 
        update_data: Dict[str, Any]
    ) -> Optional[HRInterviewModel]:
        """Update HR interview record."""
        interview = await self.get_by_id(hr_interview_id)
        if not interview:
            return None
        
        for key, value in update_data.items():
            setattr(interview, key, value)
        
        interview.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(interview)
        return interview

    async def start_interview(
        self, 
        hr_interview_id: UUID
    ) -> Optional[HRInterviewModel]:
        """Mark interview as started."""
        return await self.update_interview(
            hr_interview_id,
            {
                "interview_status": "in_progress",
                "interview_started_at": datetime.now(timezone.utc)
            }
        )

    async def complete_interview(
        self, 
        hr_interview_id: UUID, 
        completion_data: Dict[str, Any]
    ) -> Optional[HRInterviewModel]:
        """Complete interview with all results."""
        completion_data["interview_status"] = "completed"
        completion_data["interview_ended_at"] = datetime.now(timezone.utc)
        return await self.update_interview(hr_interview_id, completion_data)

    async def get_interviews_by_job(
        self, 
        job_requirement_id: UUID,
        status: Optional[str] = None
    ) -> List[HRInterviewModel]:
        """Get all interviews for a job requirement."""
        conditions = [
            HRInterviewModel.job_requirement_id == job_requirement_id,
            HRInterviewModel.status != "deleted"
        ]
        
        if status:
            conditions.append(HRInterviewModel.interview_status == status)
        
        query = select(HRInterviewModel).where(
            and_(*conditions)
        ).order_by(desc(HRInterviewModel.created_at))
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_completed_interviews_by_job_sorted_by_score(
        self, 
        job_requirement_id: UUID
    ) -> List[HRInterviewModel]:
        """Get all completed interviews for a job, sorted by overall score (descending)."""
        query = select(HRInterviewModel).where(
            and_(
                HRInterviewModel.job_requirement_id == job_requirement_id,
                HRInterviewModel.interview_status == "completed",
                HRInterviewModel.overall_score.isnot(None),
                HRInterviewModel.status != "deleted"
            )
        ).order_by(desc(HRInterviewModel.overall_score))
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_interviews_by_candidate(
        self, 
        candidate_id: UUID
    ) -> List[HRInterviewModel]:
        """Get all interviews for a candidate."""
        query = select(HRInterviewModel).where(
            and_(
                HRInterviewModel.candidate_id == candidate_id,
                HRInterviewModel.status != "deleted"
            )
        ).order_by(desc(HRInterviewModel.created_at))
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_interview_statistics(
        self, 
        job_requirement_id: UUID
    ) -> Dict[str, Any]:
        """Get interview statistics for a job requirement."""
        interviews = await self.get_interviews_by_job(job_requirement_id)
        
        completed = [i for i in interviews if i.interview_status == "completed"]
        
        if not completed:
            return {
                "total_interviews": len(interviews),
                "completed_interviews": 0,
                "pending_interviews": len([i for i in interviews if i.interview_status == "pending"]),
                "in_progress_interviews": len([i for i in interviews if i.interview_status == "in_progress"]),
                "average_score": None,
                "highest_score": None,
                "lowest_score": None,
                "passed_count": 0,
                "failed_count": 0
            }
        
        scores = [i.overall_score for i in completed if i.overall_score is not None]
        
        return {
            "total_interviews": len(interviews),
            "completed_interviews": len(completed),
            "pending_interviews": len([i for i in interviews if i.interview_status == "pending"]),
            "in_progress_interviews": len([i for i in interviews if i.interview_status == "in_progress"]),
            "average_score": sum(scores) / len(scores) if scores else None,
            "highest_score": max(scores) if scores else None,
            "lowest_score": min(scores) if scores else None,
            "passed_count": len([i for i in completed if i.result == "pass"]),
            "failed_count": len([i for i in completed if i.result == "fail"])
        }

    async def check_interview_exists(
        self, 
        candidate_id: UUID, 
        job_requirement_id: UUID
    ) -> bool:
        """Check if a completed interview already exists for this candidate and job."""
        interview = await self.get_by_candidate_and_job(candidate_id, job_requirement_id)
        return interview is not None and interview.interview_status == "completed"
