# pylint: disable=R0903,C0115,E9910,E9912,E9913
from sqlalchemy import Column, String
from app.model.baseapp_model import Base

class MigrationModel(Base):
    __tablename__ = "alembic_version"
    version_num = Column(String(32), primary_key=True)
