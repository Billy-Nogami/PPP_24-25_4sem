from sqlalchemy import Column, Integer, String, Text
from app.db.session import Base

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, index=True)
    status = Column(String, default="pending")
    result = Column(Text, nullable=True)