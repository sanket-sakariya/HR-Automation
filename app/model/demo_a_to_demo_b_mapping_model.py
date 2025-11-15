import uuid

from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.model.baseapp_model import BaseAppModel


class DemoAToDemoBMappingModel(BaseAppModel):
    """Mapping model between Demo A and Demo B."""
    __tablename__ = "demo_a_to_demo_b_mapping"
    
    mapping_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    demo_a_id = Column(UUID(as_uuid=True), ForeignKey("demo_a.demo_a_id"), nullable=False, index=True)
    demo_b_id = Column(UUID(as_uuid=True), ForeignKey("demo_b.demo_b_id"), nullable=False, index=True)
