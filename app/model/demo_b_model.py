import uuid

from sqlalchemy import Column, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.model.baseapp_model import BaseAppModel


class DemoBModel(BaseAppModel):
    """Demo B model."""
    __tablename__ = "demo_b"
    demo_b_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, info={"search": True}, index=True)
    description = Column(Text, nullable=True)
