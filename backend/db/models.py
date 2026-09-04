"""
SQLAlchemy Models
==================
Defines database tables for the AI Interview Coach.
"""

import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from db.database import Base


class User(Base):
    """User accounts."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    interviews = relationship("Interview", back_populates="user", cascade="all, delete-orphan")


class Resume(Base):
    """Uploaded resumes/CVs."""
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    job_title = Column(String, nullable=True)
    parsed_data = Column(JSON, default=dict)
    cv_review = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="resumes")
    interviews = relationship("Interview", back_populates="resume")


class Interview(Base):
    """Interview sessions."""
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=True)
    job_title = Column(String, nullable=False)
    mode = Column(String, default="direct")  # 'practice' or 'direct'
    status = Column(String, default="in_progress")  # 'in_progress', 'completed', 'abandoned'
    questions = Column(JSON, default=list)
    current_question_index = Column(Integer, default=0)
    report = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="interviews")
    resume = relationship("Resume", back_populates="interviews")
    answers = relationship("Answer", back_populates="interview", cascade="all, delete-orphan")


class Answer(Base):
    """Individual answers to interview questions."""
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False)
    question_number = Column(Integer, nullable=False)
    question = Column(Text, nullable=False)
    question_type = Column(String, nullable=False)
    transcription = Column(Text, default="")
    audio_path = Column(String, nullable=True)
    content_score = Column(Float, default=0)
    confidence_score = Column(Float, default=0)
    combined_score = Column(Float, default=0)
    content_feedback = Column(Text, default="")
    confidence_feedback = Column(Text, default="")
    tips = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    interview = relationship("Interview", back_populates="answers")
