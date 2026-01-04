import uuid
from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.model.baseapp_model import BaseAppModel


class CompanyModel(BaseAppModel):
    """Company model for company management."""

    __tablename__ = "companies"

    company_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_name = Column(String(200), nullable=False, info={"search": True}, index=True)
    email = Column(String(255), nullable=False, index=True)
    industry = Column(String(100), nullable=False)
    size = Column(String(20), nullable=False)  # 1-10, 11-50, 51-200, 201-500, 501-1000, 1001+
    website = Column(String(255), nullable=True)
    address = Column(JSONB, nullable=True)  # Store address as JSON: {street, city, state, country, zipCode}
    phone = Column(String(20), nullable=True)
    logo = Column(String(500), nullable=True)  # URL to logo
    subscription_plan = Column(String(20), nullable=True)  # starter, professional, enterprise
    is_active = Column(Boolean, nullable=False, default=True)
