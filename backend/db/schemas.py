"""
Pydantic Schemas
================
Request/response models for the API.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr


# ──────────────────────────────────────────────
# Auth Schemas
# ──────────────────────────────────────────────
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ──────────────────────────────────────────────
# Resume Schemas
# ──────────────────────────────────────────────
class ResumeResponse(BaseModel):
    id: int
    filename: str
    job_title: Optional[str]
    parsed_data: Dict[str, Any]
    cv_review: Dict[str, Any]

    class Config:
        from_attributes = True


class CVReviewResponse(BaseModel):
    score: int
    grade: str
    grade_label: str
    sections_found: Dict[str, bool]
    issues: List[Dict[str, Any]]
    strengths: List[str]
    improvement_plan: List[str]
    summary: str
    word_count: int


# ──────────────────────────────────────────────
# Interview Schemas
# ──────────────────────────────────────────────
class InterviewCreate(BaseModel):
    resume_id: Optional[int] = None
    job_title: str
    mode: str = "practice"  # 'practice', 'direct', or 'mock'
    difficulty: Optional[str] = "mid"  # 'junior', 'mid', 'senior'
    language: Optional[str] = "en"  # 'en' or 'ur'


class QuestionResponse(BaseModel):
    number: int
    question: str
    type: str
    difficulty: str
    expected_keywords: List[str]
    is_follow_up: bool = False
    question_ur: Optional[str] = None
    question_roman_ur: Optional[str] = None


class InterviewResponse(BaseModel):
    id: int
    job_title: str
    mode: str
    status: str
    current_question_index: int
    total_questions: int
    questions: List[QuestionResponse]

    class Config:
        from_attributes = True


class AnswerResponse(BaseModel):
    question_number: int
    question: str
    question_type: str
    transcription: str
    content_score: float
    confidence_score: float
    combined_score: float
    content_feedback: str
    confidence_feedback: str
    tips: List[str]
    real_time_tip: Optional[str]
    next_question: Optional[QuestionResponse]


class ReportResponse(BaseModel):
    overall_score: float
    content_average: float
    confidence_average: float
    grade: str
    grade_label: str
    strengths: List[str]
    weaknesses: List[str]
    tips: List[str]
    question_results: List[Dict[str, Any]]
    summary: str
    job_title: str
    mode: str
