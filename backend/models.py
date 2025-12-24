from sqlalchemy import Boolean, Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)

class EmotionLog(Base):
    __tablename__ = "emotion_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    emotion = Column(String)
    score = Column(Float)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    description = Column(String, nullable=True)
    duration = Column(Integer)
    duration_unit = Column(String)  # 'days', 'weeks', 'months'
    priority = Column(String)  # 'High', 'Medium', 'Low'
    status = Column(String, default="not_started")  # 'not_started', 'in_progress', 'completed'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    subtasks = Column(Text, nullable=True)  # JSON string of subtasks

class UserFact(Base):
    __tablename__ = "user_facts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    fact_text = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
