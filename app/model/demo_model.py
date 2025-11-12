import uuid
import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    Text,
    Date,
    DateTime,
    Enum,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from app.model.baseapp_model import BaseAppModel
import enum


class DemoStatus(enum.Enum):
    CREATING = "creating"
    CREATED = "created"
    DELETING = "deleting"
    DELETED = "deleted"
    UPDATING = "updating"
    UPDATED = "updated"


class DemoModel(BaseAppModel):
    """Demo model."""
    __tablename__ = "demo"
    demo_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
    workspace_id = Column(UUID(as_uuid=True), nullable=True)
    user_id = Column(UUID(as_uuid=True), nullable=True)