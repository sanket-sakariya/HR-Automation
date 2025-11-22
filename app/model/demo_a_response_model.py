import uuid

from sqlalchemy import Column, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.model.baseapp_model import BaseAppModel


class DemoAResponseModel(BaseAppModel):
    """Demo A Response model."""

    __tablename__ = "demo_a_response"
    demo_a_response_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    demo_a_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(200), nullable=False, info={"search": True}, index=True)
    description = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    error_user_message = Column(Text, nullable=True)
