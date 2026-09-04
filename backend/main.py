"""
AI Interview Coach — FastAPI Server
====================================
Backend server with user authentication, database storage, CV review,
adaptive interviews, and confidence scoring.

Public API (used by frontend):
  POST /api/auth/register
  POST /api/auth/login
  GET  /api/auth/me
  GET  /api/resumes
  POST /api/resumes/upload
  GET  /api/resumes/{id}/review
  POST /api/interviews
  GET  /api/interviews/{id}
  POST /api/interviews/{id}/answer
  GET  /api/interviews/{id}/report

All other paths serve the frontend.
"""

import os
import sys
import re
import shutil
import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

# ── Add backend to path ──
sys.path.insert(0, str(Path(__file__).parent))

# AI models
from models.resume_parser import parse_resume
from models.cv_reviewer import review_cv, match_job_description
from models.interview_engine import build_interview_plan, generate_tip, maybe_add_follow_up, generate_model_answer
from models.speech_to_text import transcribe_audio
from models.answer_evaluator import evaluate_answer
from models.confidence_detector import detect_confidence
from models.report_generator import compile_question_result, generate_report

# Database
from db.database import get_db, init_db
from db.models import User, Resume, Interview, Answer
from db.auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, require_user,
)
from db.schemas import (
    UserCreate, UserLogin, TokenResponse, UserResponse,
    InterviewCreate, InterviewResponse, AnswerResponse,
    CVReviewResponse, ReportResponse,
)


# ──────────────────────────────────────────────
# App initialization
# ──────────────────────────────────────────────
app = FastAPI(
    title="AI Interview Coach",
    description="AI Interview Coach with Auth, CV Review, and Adaptive Interviews",
    version="2.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Directories ──
BASE_DIR = Path(__file__).parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
FRONTEND_DIR = BASE_DIR / "frontend"
UPLOAD_DIR.mkdir(exist_ok=True)

# ── Static files ──
if FRONTEND_DIR.exists():
    css_dir = FRONTEND_DIR / "css"
    js_dir = FRONTEND_DIR / "js"
    if css_dir.exists():
        app.mount("/css", StaticFiles(directory=str(css_dir)), name="css")
    if js_dir.exists():
        app.mount("/js", StaticFiles(directory=str(js_dir)), name="js")
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# ──────────────────────────────────────────────
# Startup: initialize database
# ──────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    init_db()


# ═══════════════════════════════════════════════
# AUTHENTICATION
# ═══════════════════════════════════════════════

@app.post("/api/auth/register", response_model=TokenResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user account."""
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(400, "Email already registered")

    new_user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token({"sub": str(new_user.id)})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": new_user,
    }


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Login and get JWT token."""
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user:
        raise HTTPException(401, "Account not found with this email. Please click the 'Register' tab to create an account.")
    if not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(401, "Incorrect password. Please check your password and try again.")

    token = create_access_token({"sub": str(user.id)})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user,
    }


@app.get("/api/auth/me", response_model=UserResponse)
async def get_me(user: User = Depends(require_user)):
    """Get current logged-in user."""
    return user


# ═══════════════════════════════════════════════
# RESUME / CV
# ═══════════════════════════════════════════════

@app.get("/api/resumes")
async def list_resumes(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """List all resumes uploaded by the current user."""
    resumes = db.query(Resume).filter(Resume.user_id == user.id).order_by(Resume.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "filename": r.filename,
            "job_title": r.job_title,
            "target_role": r.job_title or "Software Engineer",
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "score": (r.cv_review.get("score") if (r.cv_review and isinstance(r.cv_review, dict)) else 75),
            "cv_score": (r.cv_review.get("score") if (r.cv_review and isinstance(r.cv_review, dict)) else 75),
        }
        for r in resumes
    ]


@app.post("/api/resumes/upload")
async def upload_resume(
    resume: UploadFile = File(...),
    job_title: Optional[str] = Form(None),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Upload a resume, parse it, and run CV review."""
    if not resume.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Please upload a PDF file")

    # Save file
    user_dir = UPLOAD_DIR / f"user_{user.id}"
    user_dir.mkdir(exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"resume_{timestamp}.pdf"
    file_path = user_dir / filename

    with open(file_path, "wb") as f:
        content = await resume.read()
        f.write(content)

    try:
        parsed = parse_resume(str(file_path))
        cv_review = review_cv(str(file_path))

        db_resume = Resume(
            user_id=user.id,
            filename=resume.filename,
            file_path=str(file_path),
            job_title=job_title,
            parsed_data=parsed,
            cv_review=cv_review,
        )
        db.add(db_resume)
        db.commit()
        db.refresh(db_resume)

        return {
            "id": db_resume.id,
            "filename": db_resume.filename,
            "job_title": db_resume.job_title,
            "parsed_data": parsed,
            "cv_review": cv_review,
        }

    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Resume processing failed: {str(e)}")


@app.get("/api/resumes/{resume_id}/review")
async def get_cv_review(
    resume_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Get the CV review for a specific resume."""
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user.id).first()
    if not resume:
        raise HTTPException(404, "Resume not found")

    review_data = dict(resume.cv_review) if (resume.cv_review and isinstance(resume.cv_review, dict)) else {}
    review_data["id"] = resume.id
    review_data["filename"] = resume.filename
    review_data["target_role"] = resume.job_title or "Software Engineer"
    review_data["job_title"] = resume.job_title or "Software Engineer"
    review_data["parsed_data"] = resume.parsed_data or {}
    return review_data


@app.delete("/api/resumes/{resume_id}")
async def delete_resume(
    resume_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Delete a resume and its uploaded file."""
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user.id).first()
    if not resume:
        raise HTTPException(404, "Resume not found")

    try:
        file_path = Path(resume.file_path)
        if file_path.exists():
            file_path.unlink()
    except Exception as e:
        print(f"[Delete Resume] Could not delete file: {e}")

    db.delete(resume)
    db.commit()

    return {"success": True, "message": "Resume deleted"}


@app.post("/api/resumes/{resume_id}/match-jd")
async def match_jd(
    resume_id: int,
    payload: dict,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Match resume with target job description text and return skill gap analysis."""
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user.id).first()
    if not resume:
        raise HTTPException(404, "Resume not found")

    jd_text = payload.get("jd_text", "")
    resume_text = resume.parsed_data.get("raw_text", "") if resume.parsed_data else ""
    resume_skills = resume.parsed_data.get("skills", []) if resume.parsed_data else []

    result = match_job_description(resume_text, jd_text, resume_skills=resume_skills)
    return result


# ═══════════════════════════════════════════════
# INTERVIEWS
# ═══════════════════════════════════════════════

@app.post("/api/interviews")
async def create_interview(
    data: InterviewCreate,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Create a new interview session with adaptive questions."""
    resume = None
    if data.resume_id:
        resume = db.query(Resume).filter(Resume.id == data.resume_id, Resume.user_id == user.id).first()
    if not resume:
        resume = db.query(Resume).filter(Resume.user_id == user.id).order_by(Resume.created_at.desc()).first()

    raw_mode = (data.mode or "practice").lower()
    if raw_mode in ["mock", "simulation", "direct", "timed"]:
        engine_mode = "direct"
    else:
        engine_mode = "practice"

    resume_data = resume.parsed_data if (resume and resume.parsed_data) else {"name": user.full_name, "skills": [], "experience_years": 2}
    resume_id_val = resume.id if resume else None

    target_count = data.question_count if (data.question_count and data.question_count in [3, 5, 10, 15]) else 5

    # Generate adaptive interview plan
    questions = build_interview_plan(
        resume_data=resume_data,
        job_title=data.job_title,
        mode=engine_mode,
        total_questions=target_count,
        difficulty=data.difficulty or "mid",
    )

    # Strictly guarantee exact question count
    questions = questions[:target_count]
    for idx, q in enumerate(questions):
        q["number"] = idx + 1

    interview = Interview(
        user_id=user.id,
        resume_id=resume_id_val,
        job_title=data.job_title,
        mode=data.mode or "practice",
        questions=questions,
        current_question_index=0,
        status="in_progress",
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)

    return {
        "id": interview.id,
        "job_title": interview.job_title,
        "mode": interview.mode,
        "status": interview.status,
        "current_question_index": interview.current_question_index,
        "total_questions": len(questions),
        "questions": questions,
    }


@app.get("/api/interviews")
async def list_interviews(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """List recent interviews for the current user (latest 3)."""
    interviews = db.query(Interview).filter(Interview.user_id == user.id).order_by(Interview.created_at.desc()).limit(3).all()
    return [
        {
            "id": i.id,
            "job_title": i.job_title,
            "mode": i.mode,
            "status": i.status,
            "total_questions": len(i.questions),
            "answered_count": i.current_question_index,
            "created_at": i.created_at.isoformat() if i.created_at else None,
            "completed_at": i.completed_at.isoformat() if i.completed_at else None,
        }
        for i in interviews
    ]


@app.get("/api/interviews/{interview_id}")
async def get_interview(
    interview_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Get interview session details."""
    interview = db.query(Interview).filter(Interview.id == interview_id, Interview.user_id == user.id).first()
    if not interview:
        raise HTTPException(404, "Interview not found")

    return {
        "id": interview.id,
        "resume_id": interview.resume_id,
        "job_title": interview.job_title,
        "mode": interview.mode,
        "status": interview.status,
        "current_question_index": interview.current_question_index,
        "answered_count": interview.current_question_index,
        "total_questions": len(interview.questions),
        "questions": interview.questions,
        # Resume data so the frontend can resume an in-progress interview
        "resume_parsed_data": interview.resume.parsed_data if interview.resume else {},
    }


@app.delete("/api/interviews/{interview_id}")
async def delete_interview(
    interview_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Delete an interview and all of its answers/audio files."""
    interview = db.query(Interview).filter(Interview.id == interview_id, Interview.user_id == user.id).first()
    if not interview:
        raise HTTPException(404, "Interview not found")

    # Remove stored answer audio files for this interview
    try:
        user_dir = UPLOAD_DIR / f"user_{user.id}"
        if user_dir.exists():
            for f in user_dir.glob(f"interview_{interview_id}_q*"):
                try:
                    f.unlink()
                except Exception:
                    pass
    except Exception as e:
        print(f"[Delete Interview] Could not delete audio files: {e}")

    db.delete(interview)
    db.commit()

    return {"success": True, "message": "Interview deleted"}


@app.post("/api/interviews/{interview_id}/answer")
async def submit_answer(
    interview_id: int,
    question_number: Optional[int] = Form(None),
    question_index: Optional[int] = Form(None),
    answer_text: Optional[str] = Form(None),
    audio: Optional[UploadFile] = File(None),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Submit a voice answer for the current question."""
    interview = db.query(Interview).filter(Interview.id == interview_id, Interview.user_id == user.id).first()
    if not interview:
        raise HTTPException(404, "Interview not found")

    if interview.status == "completed":
        raise HTTPException(400, "Interview already completed")

    # Resolve question number (1-based)
    resolved_q_num = question_number
    if resolved_q_num is None:
        if question_index is not None:
            resolved_q_num = question_index + 1
        else:
            resolved_q_num = interview.current_question_index + 1

    # Find question
    question = None
    for q in interview.questions:
        if q.get("number") == resolved_q_num:
            question = q
            break

    if not question:
        if interview.questions and 0 <= (resolved_q_num - 1) < len(interview.questions):
            question = interview.questions[resolved_q_num - 1]
        else:
            raise HTTPException(404, "Question not found")

    user_dir = UPLOAD_DIR / f"user_{user.id}"
    user_dir.mkdir(parents=True, exist_ok=True)
    audio_path = None

    if audio and audio.filename:
        audio_ext = Path(audio.filename).suffix or ".wav"
        audio_path = user_dir / f"interview_{interview_id}_q{resolved_q_num}{audio_ext}"
        with open(audio_path, "wb") as f:
            content = await audio.read()
            f.write(content)

    try:
        if audio_path and audio_path.exists():
            clean_vocab_prompt = "Technical software engineering mock interview answer covering skills, projects, and architecture."
            transcription = transcribe_audio(str(audio_path), language="en", prompt=clean_vocab_prompt)
            if not transcription.get("text") and answer_text:
                transcription["text"] = answer_text
            confidence = detect_confidence(str(audio_path))
        else:
            text_ans = answer_text or "I explained the key architectural and practical concepts."
            transcription = {"text": text_ans, "words_per_minute": 135.0, "duration": 25.0}
            confidence = {
                "confidence_score": 82.0,
                "speaking_pace_wpm": 135.0,
                "feedback": "Clear delivery with good focus.",
                "filler_word_count": 0,
                "filler_words_used": [],
                "duration_seconds": 25.0
            }

        content_eval = evaluate_answer(
            answer_text=transcription["text"],
            question=question["question"],
            expected_keywords=question.get("expected_keywords", []),
            question_type=question.get("type", "general"),
        )

        # Real-time tip (only in practice mode)
        real_time_tip = generate_tip(content_eval, confidence, mode=interview.mode)

        # Compile result
        result = compile_question_result(
            question=question,
            transcription=transcription,
            content_eval=content_eval,
            confidence=confidence,
        )

        # Remove any previous answer for this question (supports re-record in practice mode)
        db.query(Answer).filter(
            Answer.interview_id == interview.id,
            Answer.question_number == resolved_q_num,
        ).delete(synchronize_session=False)

        # Save answer to DB
        answer = Answer(
            interview_id=interview.id,
            question_number=resolved_q_num,
            question=question["question"],
            question_type=question["type"],
            transcription=result["transcription"],
            audio_path=str(audio_path) if audio_path else None,
            content_score=result["content_score"],
            confidence_score=result["confidence_score"],
            combined_score=result["combined_score"],
            content_feedback=result["content_feedback"],
            confidence_feedback=result["confidence_feedback"],
            tips=result["content_tips"] + result["confidence_tips"],
        )
        db.add(answer)

        # Update interview progress
        interview.current_question_index = resolved_q_num

        # Keep question count bounded to what user requested
        last_answer = transcription["text"]
        updated_questions = maybe_add_follow_up(
            interview.questions,
            last_answer,
            question,
            max_questions=len(interview.questions),
        )
        interview.questions = updated_questions

        # Check if interview completed
        if resolved_q_num >= len(interview.questions):
            interview.status = "completed"
            interview.completed_at = datetime.datetime.utcnow()

        db.commit()
        db.refresh(answer)

        # Find next question
        next_question = None
        if resolved_q_num < len(interview.questions):
            next_q = interview.questions[resolved_q_num]
            next_question = {
                "number": next_q["number"],
                "question": next_q["question"],
                "type": next_q["type"],
                "difficulty": next_q["difficulty"],
                "expected_keywords": next_q.get("expected_keywords", []),
                "is_follow_up": next_q.get("is_follow_up", False),
            }

        return {
            "question_number": result["question_number"],
            "question": result["question"],
            "question_type": result["question_type"],
            "transcription": result["transcription"],
            "content_score": result["content_score"],
            "confidence_score": result["confidence_score"],
            "combined_score": result["combined_score"],
            "content_feedback": result["content_feedback"],
            "confidence_feedback": result["confidence_feedback"],
            "tips": result["content_tips"] + result["confidence_tips"],
            "real_time_tip": real_time_tip,
            "next_question": next_question,
        }

    except Exception as e:
        raise HTTPException(500, f"Answer processing failed: {str(e)}")


@app.post("/api/interviews/{interview_id}/skip")
async def skip_question(
    interview_id: int,
    payload: dict = Body(default={}),
    question_number: Optional[int] = Form(None),
    question_index: Optional[int] = Form(None),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Skip / Pass the current question without requiring voice answer."""
    interview = db.query(Interview).filter(Interview.id == interview_id, Interview.user_id == user.id).first()
    if not interview:
        raise HTTPException(404, "Interview not found")

    # Resolve question number (1-based)
    resolved_q_num = None
    if isinstance(payload, dict):
        if payload.get("question_number") is not None:
            resolved_q_num = int(payload["question_number"])
        elif payload.get("question_index") is not None:
            resolved_q_num = int(payload["question_index"]) + 1

    if resolved_q_num is None:
        if question_number is not None:
            resolved_q_num = question_number
        elif question_index is not None:
            resolved_q_num = question_index + 1
        else:
            resolved_q_num = interview.current_question_index + 1

    # Find question
    question = None
    for q in (interview.questions or []):
        if q.get("number") == resolved_q_num:
            question = q
            break

    if not question:
        if interview.questions and 0 <= (resolved_q_num - 1) < len(interview.questions):
            question = interview.questions[resolved_q_num - 1]
        else:
            resolved_q_num = len(interview.questions) if interview.questions else 1
            question = interview.questions[-1] if interview.questions else {"question": "Interview Question", "type": "technical"}

    # Remove any previous answer for this question
    db.query(Answer).filter(
        Answer.interview_id == interview.id,
        Answer.question_number == resolved_q_num,
    ).delete(synchronize_session=False)

    # Save skipped answer to DB
    skipped_tips = [
        "In a live interview, try to explain your thought process even if you don't know the full answer.",
        "Break down technical questions into smaller components using the STAR technique.",
    ]
    answer = Answer(
        interview_id=interview.id,
        question_number=resolved_q_num,
        question=question.get("question", f"Question {resolved_q_num}"),
        question_type=question.get("type", "general"),
        transcription="[Question skipped / passed by candidate]",
        audio_path="",
        content_score=0.0,
        confidence_score=0.0,
        combined_score=0.0,
        content_feedback="Question was skipped. Tip: When unsure, articulating your problem-solving approach makes a better impression than passing entirely.",
        confidence_feedback="Skipped without audio recording.",
        tips=skipped_tips,
    )
    db.add(answer)

    # Update interview progress
    interview.current_question_index = resolved_q_num

    # Check if interview completed
    if resolved_q_num >= len(interview.questions or []):
        interview.status = "completed"
        interview.completed_at = datetime.datetime.utcnow()

    db.commit()
    db.refresh(answer)

    # Find next question
    next_question = None
    if resolved_q_num < len(interview.questions or []):
        next_q = interview.questions[resolved_q_num]
        next_question = {
            "number": next_q.get("number", resolved_q_num + 1),
            "question": next_q.get("question", ""),
            "type": next_q.get("type", "general"),
            "difficulty": next_q.get("difficulty", "medium"),
            "expected_keywords": next_q.get("expected_keywords", []),
            "is_follow_up": next_q.get("is_follow_up", False),
        }

    return {
        "question_number": resolved_q_num,
        "question": question.get("question", f"Question {resolved_q_num}"),
        "question_type": question.get("type", "general"),
        "transcription": "[Question skipped / passed by candidate]",
        "content_score": 0.0,
        "confidence_score": 0.0,
        "combined_score": 0.0,
        "content_feedback": "Question was skipped.",
        "confidence_feedback": "Skipped without audio recording.",
        "tips": skipped_tips,
        "real_time_tip": "Tip: In technical interviews, attempting partial solutions demonstrates resilience and analytical thinking.",
        "next_question": next_question,
        "is_skipped": True,
    }


@app.get("/api/interviews/{interview_id}/report")
async def get_report(
    interview_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Get final interview report."""
    interview = db.query(Interview).filter(Interview.id == interview_id, Interview.user_id == user.id).first()
    if not interview:
        raise HTTPException(404, "Interview not found")

    answers = db.query(Answer).filter(Answer.interview_id == interview.id).order_by(Answer.question_number).all()

    answer_map = {ans.question_number: ans for ans in answers}
    question_results = []

    for idx, q in enumerate(interview.questions or []):
        q_num = idx + 1
        if q_num in answer_map:
            ans = answer_map[q_num]
            question_results.append({
                "question_number": ans.question_number,
                "question": ans.question,
                "question_type": ans.question_type,
                "transcription": ans.transcription or "[Answer recorded]",
                "content_score": ans.content_score,
                "confidence_score": ans.confidence_score,
                "combined_score": ans.combined_score,
                "content_feedback": ans.content_feedback,
                "confidence_feedback": ans.confidence_feedback,
                "content_breakdown": {},
                "confidence_breakdown": {},
            })
        else:
            question_results.append({
                "question_number": q_num,
                "question": q.get("question", f"Question {q_num}"),
                "question_type": q.get("type", "general"),
                "transcription": "[Question skipped / passed by candidate]",
                "content_score": 0.0,
                "confidence_score": 0.0,
                "combined_score": 0.0,
                "content_feedback": "This question was skipped during the interview.",
                "confidence_feedback": "Skipped without audio recording.",
                "content_breakdown": {},
                "confidence_breakdown": {},
            })

    valid_answers = [a for a in answers if (a.content_score > 0 or a.confidence_score > 0)]

    if valid_answers:
        report = generate_report(
            question_results=question_results,
            resume_data=interview.resume.parsed_data if interview.resume else None,
            job_title=interview.job_title,
        )
    else:
        # All skipped
        report = {
            "overall_score": 0.0,
            "content_score": 0.0,
            "content_average": 0.0,
            "confidence_score": 0.0,
            "confidence_average": 0.0,
            "pace_wpm": 0,
            "grade": "N/A",
            "grade_label": "Incomplete / All Skipped",
            "strengths": ["Completed interview session walkthrough."],
            "weaknesses": ["All interview questions were skipped without answering."],
            "improvements": ["Practice speaking answers aloud or typing in the answer drawer to build your AI readiness score."],
            "tips": ["Aim to speak for at least 30-45 seconds per question using the STAR method (Situation, Task, Action, Result)."],
            "question_results": question_results,
            "summary": f"Interview session for {interview.job_title} completed. All questions were passed/skipped without answers.",
            "job_title": interview.job_title,
            "mode": interview.mode,
            "created_at": interview.created_at.isoformat() if interview.created_at else None,
        }

    # Format questions list for frontend consumption
    report["questions"] = [
        {
            "question": qr["question"],
            "score": round(qr.get("combined_score") or qr.get("content_score") or 0, 1),
            "user_answer": qr.get("transcription", "Skipped"),
            "feedback": qr.get("content_feedback", "Completed"),
        }
        for qr in question_results
    ]

    report["mode"] = interview.mode
    interview.report = report
    interview.status = "completed"
    if not interview.completed_at:
        interview.completed_at = datetime.datetime.utcnow()
    db.commit()

    return report


@app.get("/api/interviews/{interview_id}/model-answer")
async def get_model_answer(
    interview_id: int,
    question_number: Optional[int] = None,
    question_index: Optional[int] = None,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    resolved_num = question_number
    if resolved_num is None:
        resolved_num = (question_index + 1) if question_index is not None else 1
    """Generate a model/sample answer for a question (practice mode)."""
    interview = db.query(Interview).filter(Interview.id == interview_id, Interview.user_id == user.id).first()
    if not interview:
        raise HTTPException(404, "Interview not found")

    question = None
    for q in interview.questions:
        if q.get("number") == resolved_num or q.get("number") == (resolved_num - 1):
            question = q
            break

    if not question:
        raise HTTPException(404, "Question not found")

    resume_data = interview.resume.parsed_data if interview.resume else {}
    model_answer = generate_model_answer(
        question=question,
        resume_data=resume_data,
        job_title=interview.job_title,
    )

    return {
        "question_number": resolved_num,
        "question": question["question"],
        "model_answer": model_answer,
    }


# ═══════════════════════════════════════════════
# 5 NEW CAREER ACCELERATION AI TOOLS
# ═══════════════════════════════════════════════

from pydantic import BaseModel
from typing import List, Optional

class ATSOptimizeRequest(BaseModel):
    resume_id: Optional[int] = None
    job_description: str
    target_role: Optional[str] = "Software Engineer"

class SalaryNegotiateRequest(BaseModel):
    job_title: str = "Software Engineer"
    experience_years: Optional[int] = 2
    initial_offer: Optional[float] = 95000.0
    target_offer: Optional[float] = 120000.0
    candidate_message: Optional[str] = None
    candidate_pitch: Optional[str] = None
    strategy: Optional[str] = "Balanced"
    history: Optional[List[dict]] = []

class ElevatorPitchRequest(BaseModel):
    job_title: str
    pitch_text: str
    duration_seconds: Optional[float] = 45.0

@app.post("/api/tools/ats-optimizer")
async def ats_optimizer_endpoint(
    req: ATSOptimizeRequest,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Analyze CV against target Job Description, calculate ATS score and generate tailored bullet points."""
    resume_text = ""
    resume_skills = []
    if req.resume_id:
        query = db.query(Resume).filter(Resume.id == req.resume_id)
        if user:
            query = query.filter(Resume.user_id == user.id)
        resume = query.first()
        if resume and resume.parsed_data:
            resume_skills = [str(s).lower() for s in resume.parsed_data.get("skills", [])]
            resume_text = (resume.parsed_data.get("raw_text", "") or " ".join(resume_skills)).lower()
    elif not resume_text and user:
        latest_res = db.query(Resume).filter(Resume.user_id == user.id).order_by(Resume.created_at.desc()).first()
        if latest_res and latest_res.parsed_data:
            resume_skills = [str(s).lower() for s in latest_res.parsed_data.get("skills", [])]
            resume_text = (latest_res.parsed_data.get("raw_text", "") or " ".join(resume_skills)).lower()

    jd_lower = req.job_description.lower()
    
    # Comprehensive lexicon of 150+ tech skills across Mobile, Web, Cloud, AI, Backend
    comprehensive_skills = [
        # Mobile & Flutter
        "flutter", "dart", "android", "ios", "swift", "kotlin", "react native", "provider", "bloc",
        "riverpod", "mobx", "redux", "state management", "mobile app development", "google play",
        "app store", "cross-platform", "sqlite", "firebase", "mobile development", "fastlane",
        
        # Web & Frontend
        "react", "react.js", "next.js", "vue", "vue.js", "angular", "javascript", "typescript",
        "html", "html5", "css", "css3", "tailwind", "tailwind css", "bootstrap", "sass", "webpack",
        "vite", "zustand", "graphql", "rest api", "responsive design", "ui/ux",
        
        # Backend & Databases
        "python", "fastapi", "django", "flask", "node.js", "express", "nest.js", "java", "spring boot",
        "c#", ".net", "golang", "go", "rust", "php", "laravel", "c++", "c", "ruby", "rails",
        "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "sql", "nosql", "orm", "sqlalchemy",
        "prisma", "kafka", "rabbitmq", "celery", "grpc", "microservices", "websockets",
        
        # Cloud & DevOps
        "docker", "kubernetes", "aws", "alibaba cloud", "gcp", "azure", "terraform", "ansible",
        "ci/cd", "git", "github", "gitlab", "github actions", "jenkins", "linux", "nginx", "helm",
        "prometheus", "grafana", "serverless", "cloud architecture",
        
        # AI & Data
        "machine learning", "deep learning", "pytorch", "tensorflow", "nlp", "llm", "rag",
        "langchain", "openai", "pandas", "numpy", "scikit-learn", "computer vision", "opencv",
        "data science", "data analysis", "etl", "spark",
        
        # Practices
        "system design", "clean architecture", "mvvm", "mvc", "oop", "design patterns", "unit testing",
        "tdd", "agile", "scrum", "debugging", "performance optimization", "version control"
    ]
    
    # Extract matching skills from JD
    jd_skills = []
    for skill in comprehensive_skills:
        # Match whole words or phrases
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, jd_lower):
            jd_skills.append(skill)
    
    if not jd_skills:
        # Fallback extract words from JD
        words = re.findall(r'\b[a-zA-Z]{3,15}\b', jd_lower)
        stopwords = {"and", "the", "for", "with", "experience", "skills", "requirements", "years", "must", "have", "ability", "strong", "work", "team", "role", "full", "life", "cycle"}
        jd_skills = [w for w in set(words) if w not in stopwords][:8]

    # Deduplicate while preserving order
    seen = set()
    unique_jd_skills = []
    for s in jd_skills:
        if s not in seen:
            seen.add(s)
            unique_jd_skills.append(s)

    matched = []
    missing = []

    for s in unique_jd_skills:
        # Check if skill is in parsed resume_skills or resume raw_text
        is_matched = (
            any(s == rs or s in rs or rs in s for rs in resume_skills) or
            bool(re.search(r'\b' + re.escape(s) + r'\b', resume_text))
        )
        if is_matched:
            matched.append(s)
        else:
            missing.append(s)

    if not resume_text:
        match_pct = 50.0
    else:
        match_pct = round((len(matched) / max(1, len(unique_jd_skills))) * 100, 1)

    # Generate Tailored STAR Bullet Points tailored to the target role
    role = req.target_role or "Software Engineer"
    role_lower = role.lower()
    
    top_m = [s.title() for s in matched[:3]] or ["Modern Frameworks", "Git", "REST APIs"]
    top_miss = [s.title() for s in missing[:2]] or ["Cloud Architecture", "Automated CI/CD"]
    
    m_str = ", ".join(top_m)
    miss_str = top_miss[0] if top_miss else "Cloud CI/CD"

    if "flutter" in role_lower or "mobile" in role_lower or "dart" in role_lower or "android" in role_lower or "ios" in role_lower:
        suggested_bullets = [
            f"Engineered and deployed scalable mobile applications using Flutter and Dart, maintaining 99.8% crash-free sessions across Android (Google Play) & iOS (App Store).",
            f"Implemented clean state management architecture using {m_str}, optimizing UI rebuild lifecycle and reducing memory overhead by 35%.",
            f"Integrated secure RESTful APIs, offline SQLite caching, and asynchronous background services to ensure seamless user experience on low-connectivity networks.",
            f"Spearheaded adoption of {miss_str} and automated mobile build pipelines, reducing release deployment time by 40%."
        ]
    elif "ai" in role_lower or "data" in role_lower or "machine learning" in role_lower or "nlp" in role_lower:
        suggested_bullets = [
            f"Architected and fine-tuned domain-specific AI models and RAG pipelines using {m_str}, improving retrieval accuracy by 42% and reducing inference latency.",
            f"Designed and deployed low-latency prediction microservices with FastAPI and Docker on Cloud infrastructure, serving over 50,000+ daily user requests.",
            f"Automated data preprocessing pipelines and feature engineering workflows with Pandas and PyTorch, accelerating model training velocity by 30%.",
            f"Integrated {miss_str} monitoring and automated model evaluation benchmarks, maintaining 99.9% uptime in production environments."
        ]
    elif "cloud" in role_lower or "devops" in role_lower:
        suggested_bullets = [
            f"Architected multi-region cloud infrastructure using {m_str}, achieving 99.99% high availability and automated failover capabilities.",
            f"Built automated CI/CD deployment pipelines with Docker and Kubernetes, reducing software release cycles from weeks to under 15 minutes.",
            f"Optimized cloud computing costs by 28% through dynamic auto-scaling policies, containerized workloads, and serverless architectures.",
            f"Integrated {miss_str} monitoring, alerting, and centralized log aggregation with Prometheus and Grafana for rapid incident resolution."
        ]
    else:
        suggested_bullets = [
            f"Architected and shipped scalable software services using {m_str}, improving system throughput by 38% and reducing API response latency.",
            f"Spearheaded end-to-end integration of {miss_str} workflows, automating testing suites and achieving 99.9% production uptime.",
            f"Refactored legacy codebases to adopt modular clean architecture and unit tests, reducing bug reports by 45% and boosting team velocity.",
            f"Collaborated with cross-functional teams to deliver high-priority features for {role}, directly impacting over 25,000+ monthly active users."
        ]

    return {
        "match_score": match_pct,
        "matched_skills": [s.title() for s in matched],
        "missing_skills": [s.title() for s in missing],
        "total_jd_keywords": len(unique_jd_skills),
        "suggested_bullets": suggested_bullets,
        "ats_tips": [
            f"Ensure top matched keywords ({', '.join(top_m)}) appear in your summary and experience sections.",
            f"Add {miss_str} to your skills list or mention relevant project exposure to boost ATS keyword ranking.",
            "Start every resume bullet with a strong action verb (Architected, Engineered, Spearheaded, Optimized).",
            "Quantify your accomplishments with concrete metrics (e.g. latency reduced by 35%, 50k+ active users)."
        ]
    }


@app.post("/api/tools/salary-negotiator")
async def salary_negotiator_endpoint(
    req: SalaryNegotiateRequest,
    user: Optional[User] = Depends(get_current_user),
):
    """AI HR Recruiter salary negotiation simulation bot."""
    msg = (req.candidate_pitch or req.candidate_message or "").strip()
    msg_lower = msg.lower()
    
    # Calculate negotiation score based on tone and tactics
    score = 68.0
    feedback_points = []
    
    has_gratitude = any(w in msg_lower for w in ["thank", "appreciate", "excited", "grateful", "thrilled", "pleased"])
    has_value_prop = any(w in msg_lower for w in ["experience", "skill", "impact", "delivered", "market", "value", "track record", "results", "specialized", "built"])
    has_number = bool(re.search(r'\d+', msg))
    has_flexibility = any(w in msg_lower for w in ["flexible", "open", "total package", "equity", "bonus", "benefits", "hybrid", "package", "range"])

    if has_gratitude:
        score += 10
        feedback_points.append("✓ Great job opening with enthusiasm and professional gratitude for the offer.")
    else:
        feedback_points.append("⚠️ Tip: Always start by expressing genuine excitement for the role before discussing compensation.")

    if has_value_prop:
        score += 12
        feedback_points.append("✓ Strong justification linking your requested compensation to your proven technical skillset and market value.")
    else:
        feedback_points.append("⚠️ Tip: Anchor your counter-offer to specific past projects, business impact, or current market salary data.")

    if has_flexibility:
        score += 10
        feedback_points.append("✓ Excellent strategic flexibility regarding total rewards (performance bonuses, equity, remote flexibility).")
    else:
        feedback_points.append("⚠️ Tip: If base salary is capped, inquire about performance bonuses, signing bonuses, or accelerated review cycles.")

    score = min(98.0, max(45.0, score))

    # Determine counter adjustment
    init_offer = req.initial_offer or 95000.0
    target = req.target_offer or (init_offer * 1.2)
    
    # Adjust offer realistically based on score
    bump_ratio = 0.05 + (score / 100.0) * 0.10
    counter_bump = round(init_offer * bump_ratio, -2)
    new_offer = min(target, init_offer + counter_bump)

    if score >= 75:
        ai_reply = f"Thank you for sharing your detailed perspective and highlighting your specialized background in {req.job_title}. We are very impressed by what you bring to the table. After reviewing with our leadership team, we are excited to increase our base offer to ${int(new_offer):,}, alongside our standard annual performance bonus and comprehensive benefits package. We believe this represents a strong win-win and would love to welcome you to the team!"
    else:
        ai_reply = f"Thank you for your response. While our compensation budget for the {req.job_title} position is structured within defined organizational bands, we recognize your strong potential. We are pleased to present a revised base offer of ${int(new_offer):,}, complemented by our annual review program and flexible work benefits. Please let us know if this package works for you!"

    return {
        "negotiation_score": score,
        "tactic_score": score,
        "revised_offer": new_offer,
        "recruiter_response": ai_reply,
        "ai_response": ai_reply,
        "tactical_feedback": feedback_points,
        "tactical_advice": "When countering, always anchor to high market value and propose total package solutions (bonus, equity, flexible review)."
    }
@app.post("/api/tools/elevator-pitch")
async def elevator_pitch_endpoint(
    req: ElevatorPitchRequest,
    user: Optional[User] = Depends(get_current_user),
):
    """Analyze candidate 60-second elevator pitch."""
    text = req.pitch_text.strip()
    words = len(text.split())
    duration = req.duration_seconds or 45.0
    wpm = round((words / max(1, duration)) * 60, 1)

    hook_score = 75.0 if any(w in text.lower() for w in ["passionate", "specialize", "developer", "engineer", "build", "lead"]) else 50.0
    clarity_score = 85.0 if (70 <= wpm <= 160) else 60.0
    impact_score = 80.0 if any(w in text.lower() for w in ["project", "scaled", "delivered", "built", "designed", "impact", "production"]) else 55.0

    overall = round((hook_score * 0.3 + clarity_score * 0.3 + impact_score * 0.4), 1)

    improved_pitch = (
        f"Hi, I'm a dedicated {req.job_title} with proven expertise in building high-performance, user-centric software systems. "
        f"Over my career, I've specialized in full-stack architecture, clean API design, and deploying scalable solutions that solve real business problems. "
        f"I'm excited about this opportunity because I'm eager to bring my problem-solving drive and technical execution to help your team ship high-impact products."
    )

    return {
        "overall_score": overall,
        "hook_score": hook_score,
        "clarity_score": clarity_score,
        "impact_score": impact_score,
        "words_count": words,
        "estimated_wpm": wpm,
        "strengths": [
            "Good concise structure for technical introduction.",
            f"Speaking pace estimate: {wpm} WPM (Ideal range: 110-150 WPM)."
        ],
        "improvements": [
            "Add 1 specific standout project or metric you are proud of.",
            "End with a forward-looking statement on how you plan to contribute."
        ],
        "polished_version": improved_pitch
    }


@app.get("/api/tools/question-bank")
async def question_bank_endpoint(
    job_title: str = "Full Stack AI Developer",
    user: Optional[User] = Depends(get_current_user),
):
    """Generate categorized technical & behavioral flashcards for target role."""
    questions = [
        {
            "category": "System Architecture",
            "difficulty": "Hard",
            "question": f"How do you design a high-throughput, low-latency API architecture for a {job_title} application?",
            "key_concepts": ["Load Balancing", "Redis Caching", "Database Indexing", "Asynchronous Workers", "Connection Pooling"],
            "model_answer": "I decouple request handling using asynchronous worker queues (Celery/RabbitMQ), implement multi-tier caching with Redis, utilize connection pooling for PostgreSQL, and apply database indexing on frequent query keys with horizontal scaling behind Nginx/ALB."
        },
        {
            "category": "Frontend & Performance",
            "difficulty": "Medium",
            "question": "Explain how you optimize frontend bundle size, rendering performance, and Core Web Vitals.",
            "key_concepts": ["Code Splitting", "Tree Shaking", "Lazy Loading", "Memoization", "Asset Compression"],
            "model_answer": "I implement dynamic imports with route-based code splitting, optimize images using modern WebP formats, eliminate unused dependencies via tree shaking, and prevent unnecessary re-renders using useMemo/useCallback."
        },
        {
            "category": "Security & Auth",
            "difficulty": "Medium",
            "question": "How do you protect modern web applications against OWASP Top 10 vulnerabilities like XSS, CSRF, and SQL Injection?",
            "key_concepts": ["JWT / HttpOnly Cookies", "Parameterized Queries (ORMs)", "Content Security Policy (CSP)", "CORS"],
            "model_answer": "I store authentication tokens in Secure HttpOnly SameSite cookies to mitigate XSS theft, use ORM parameterized queries to eliminate SQL injection, configure strict CSP headers, and implement rate limiting on sensitive auth endpoints."
        },
        {
            "category": "Behavioral & Leadership",
            "difficulty": "Medium",
            "question": "Tell me about a time you disagreed with a technical architecture decision made by a senior peer or manager.",
            "key_concepts": ["STAR Method", "Objective Benchmarks", "Constructive Dialogue", "Commitment to Team Alignment"],
            "model_answer": "In a previous project, there was a proposal to use a complex distributed microservices architecture for an MVP. I prepared a benchmark comparison highlighting operational overhead vs a modular monolith. We discussed it collaboratively and agreed on a modular monolith that saved 4 weeks of launch time."
        },
        {
            "category": "Data & State Management",
            "difficulty": "Hard",
            "question": "How do you ensure data consistency and transactional integrity across distributed services?",
            "key_concepts": ["Saga Pattern", "Event Sourcing", "Idempotency Keys", "Two-Phase Commit", "Dead Letter Queues"],
            "model_answer": "I leverage the Saga pattern with compensating transactions, issue idempotency keys on write requests to prevent duplicate charging/creation, and use transactional outbox tables with message brokers like Kafka/RabbitMQ."
        }
    ]
    return {"job_title": job_title, "questions": questions}


@app.get("/api/tools/certificate/{interview_id}")
async def get_certificate_endpoint(
    interview_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Generate verified readiness certificate metadata for completed interview."""
    interview = db.query(Interview).filter(Interview.id == interview_id, Interview.user_id == user.id).first()
    if not interview:
        raise HTTPException(404, "Interview session not found.")

    overall_score = 82.5
    if interview.report and isinstance(interview.report, dict) and interview.report.get("overall_score"):
        overall_score = interview.report["overall_score"]
    elif interview.answers:
        scores = [a.combined_score or a.content_score for a in interview.answers if (a.combined_score or a.content_score)]
        if scores:
            overall_score = sum(scores) / len(scores)

    score = round(float(overall_score), 1)
    grade = "A" if score >= 85 else ("B" if score >= 70 else "C")
    
    dt = interview.completed_at or interview.created_at
    date_str = dt.strftime("%B %d, %Y") if dt else "September 2026"
    cert_hash = f"ALIBABA-PK-2026-{interview.id:04d}-{abs(hash(str(user.id) + str(interview.id))) % 10000:04d}"

    skills = ["Software Architecture", "Voice Communication", "Problem Solving"]
    if interview.resume and interview.resume.parsed_data and isinstance(interview.resume.parsed_data, dict):
        extracted = interview.resume.parsed_data.get("skills", [])
        if extracted:
            skills = extracted[:6]

    return {
        "certificate_id": cert_hash,
        "candidate_name": user.full_name or "Candidate",
        "job_title": interview.job_title,
        "overall_score": score,
        "grade": grade,
        "issue_date": date_str,
        "issuer": "Alibaba Cloud AI Hackathon Pakistan 2026",
        "credential_url": f"https://interviewcoach.ai/verify/{cert_hash}",
        "skills_verified": skills
    }


# ═══════════════════════════════════════════════
# FRONTEND CATCH-ALL
# ═══════════════════════════════════════════════

@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    """Serve static files (CSS, JS, images) or index.html for SPA."""
    if full_path:
        file_path = FRONTEND_DIR / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    raise HTTPException(404, "Frontend not found")


# ═══════════════════════════════════════════════
# RUN SERVER
# ═══════════════════════════════════════════════
if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    print("=" * 60)
    print("  AI Interview Coach v2 — Server Starting")
    print("=" * 60)
    print(f"  Frontend: {FRONTEND_DIR}")
    print(f"  Uploads:  {UPLOAD_DIR}")
    print(f"  Database: {BASE_DIR / 'data' / 'interview_coach.db'}")
    print(f"  Listening: http://{host}:{port}")
    print("=" * 60)
    uvicorn.run(app, host=host, port=port)
