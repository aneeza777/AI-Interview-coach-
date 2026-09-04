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
import shutil
import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

# ── Add backend to path ──
sys.path.insert(0, str(Path(__file__).parent))

# AI models
from models.resume_parser import parse_resume
from models.cv_reviewer import review_cv
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
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(401, "Invalid email or password")

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
            "created_at": r.created_at.isoformat(),
            "cv_score": r.cv_review.get("score") if r.cv_review else None,
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

    return resume.cv_review


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
    resume = db.query(Resume).filter(Resume.id == data.resume_id, Resume.user_id == user.id).first()
    if not resume:
        raise HTTPException(404, "Resume not found")

    if data.mode not in ["practice", "direct"]:
        raise HTTPException(400, "Mode must be 'practice' or 'direct'")

    # Generate adaptive interview plan
    questions = build_interview_plan(
        resume_data=resume.parsed_data,
        job_title=data.job_title,
        mode=data.mode,
        total_questions=10,
    )

    interview = Interview(
        user_id=user.id,
        resume_id=resume.id,
        job_title=data.job_title,
        mode=data.mode,
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
    question_number: int = Form(...),
    audio: UploadFile = File(...),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Submit a voice answer for the current question."""
    interview = db.query(Interview).filter(Interview.id == interview_id, Interview.user_id == user.id).first()
    if not interview:
        raise HTTPException(404, "Interview not found")

    if interview.status == "completed":
        raise HTTPException(400, "Interview already completed")

    # Find question
    question = None
    for q in interview.questions:
        if q["number"] == question_number:
            question = q
            break

    if not question:
        raise HTTPException(404, "Question not found")

    # Save audio
    user_dir = UPLOAD_DIR / f"user_{user.id}"
    audio_ext = Path(audio.filename).suffix or ".webm"
    audio_path = user_dir / f"interview_{interview_id}_q{question_number}{audio_ext}"

    with open(audio_path, "wb") as f:
        content = await audio.read()
        f.write(content)

    try:
        # Run AI pipeline
        prompt = f"Interview question: {question['question']}\nCandidate answer:"
        transcription = transcribe_audio(str(audio_path), prompt=prompt)
        content_eval = evaluate_answer(
            answer_text=transcription["text"],
            question=question["question"],
            expected_keywords=question.get("expected_keywords", []),
            question_type=question.get("type", "general"),
        )
        confidence = detect_confidence(str(audio_path))

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
            Answer.question_number == question_number,
        ).delete(synchronize_session=False)

        # Save answer to DB
        answer = Answer(
            interview_id=interview.id,
            question_number=question_number,
            question=question["question"],
            question_type=question["type"],
            transcription=result["transcription"],
            audio_path=str(audio_path),
            content_score=result["content_score"],
            confidence_score=result["confidence_score"],
            combined_score=result["combined_score"],
            content_feedback=result["content_feedback"],
            confidence_feedback=result["confidence_feedback"],
            tips=result["content_tips"] + result["confidence_tips"],
        )
        db.add(answer)

        # Update interview progress
        interview.current_question_index = question_number

        # Possibly add follow-up question
        last_answer = transcription["text"]
        updated_questions = maybe_add_follow_up(
            interview.questions,
            last_answer,
            question,
            max_questions=15,
        )
        interview.questions = updated_questions

        # Check if interview completed
        if question_number >= len(interview.questions):
            interview.status = "completed"
            interview.completed_at = datetime.datetime.utcnow()

        db.commit()
        db.refresh(answer)

        # Find next question
        next_question = None
        if question_number < len(interview.questions):
            next_q = interview.questions[question_number]
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

    if not answers:
        raise HTTPException(400, "No answers submitted yet")

    # Convert answers to question_results format
    question_results = []
    for ans in answers:
        question_results.append({
            "question_number": ans.question_number,
            "question": ans.question,
            "question_type": ans.question_type,
            "transcription": ans.transcription,
            "content_score": ans.content_score,
            "confidence_score": ans.confidence_score,
            "combined_score": ans.combined_score,
            "content_feedback": ans.content_feedback,
            "confidence_feedback": ans.confidence_feedback,
            "content_breakdown": {},
            "confidence_breakdown": {},
        })

    report = generate_report(
        question_results=question_results,
        resume_data=interview.resume.parsed_data if interview.resume else None,
        job_title=interview.job_title,
    )

    # Include mode in report
    report["mode"] = interview.mode

    # Cache report in interview record
    interview.report = report
    db.commit()

    return report


@app.get("/api/interviews/{interview_id}/model-answer")
async def get_model_answer(
    interview_id: int,
    question_number: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Generate a model/sample answer for a question (practice mode)."""
    interview = db.query(Interview).filter(Interview.id == interview_id, Interview.user_id == user.id).first()
    if not interview:
        raise HTTPException(404, "Interview not found")

    question = None
    for q in interview.questions:
        if q["number"] == question_number:
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
        "question_number": question_number,
        "question": question["question"],
        "model_answer": model_answer,
    }


# ═══════════════════════════════════════════════
# FRONTEND CATCH-ALL
# ═══════════════════════════════════════════════

@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    """Serve the frontend for any non-API path."""
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    raise HTTPException(404, "Frontend not found")


# ═══════════════════════════════════════════════
# RUN SERVER
# ═══════════════════════════════════════════════
if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  AI Interview Coach v2 — Server Starting")
    print("=" * 60)
    print(f"  Frontend: {FRONTEND_DIR}")
    print(f"  Uploads:  {UPLOAD_DIR}")
    print(f"  Database: {BASE_DIR / 'data' / 'interview_coach.db'}")
    print("=" * 60)
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
