import uuid

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Text,
    Date,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

from app.model.baseapp_model import BaseAppModel


class DemoAModel(BaseAppModel):
    """Demo A model."""

    __tablename__ = "demo_a"
    demo_a_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, info={"search": True}, index=True)
    description = Column(Text, nullable=True)
    website = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    age = Column(Integer, nullable=True)
    progress = Column(Float, nullable=True)
    start_date = Column(Date, nullable=True)
    social_accounts = Column(JSONB, nullable=True)
    tags = Column(ARRAY(String), nullable=True)
    preferences = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    error_user_message = Column(Text, nullable=True)
