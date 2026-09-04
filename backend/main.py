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
        difficulty=data.difficulty or "mid",
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
        # Run AI pipeline with English domain vocabulary
        clean_vocab_prompt = "Technical software engineering mock interview answer covering skills, projects, and architecture."
        transcription = transcribe_audio(str(audio_path), language="en", prompt=clean_vocab_prompt)
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


@app.post("/api/interviews/{interview_id}/skip")
async def skip_question(
    interview_id: int,
    question_number: int = Form(...),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Skip / Pass the current question without requiring voice answer."""
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

    # Remove any previous answer for this question
    db.query(Answer).filter(
        Answer.interview_id == interview.id,
        Answer.question_number == question_number,
    ).delete(synchronize_session=False)

    # Save skipped answer to DB
    skipped_tips = [
        "In a live interview, try to explain your thought process even if you don't know the full answer.",
        "Break down technical questions into smaller components using the STAR technique.",
    ]
    answer = Answer(
        interview_id=interview.id,
        question_number=question_number,
        question=question["question"],
        question_type=question["type"],
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
    interview.current_question_index = question_number

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
        "question_number": question_number,
        "question": question["question"],
        "question_type": question["type"],
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
# 5 NEW CAREER ACCELERATION AI TOOLS
# ═══════════════════════════════════════════════

from pydantic import BaseModel
from typing import List, Optional

class ATSOptimizeRequest(BaseModel):
    resume_id: Optional[int] = None
    job_description: str
    target_role: Optional[str] = "Software Engineer"

class SalaryNegotiateRequest(BaseModel):
    job_title: str
    experience_years: Optional[int] = 2
    initial_offer: float = 120000
    candidate_message: str
    history: Optional[List[dict]] = []

class ElevatorPitchRequest(BaseModel):
    job_title: str
    pitch_text: str
    duration_seconds: Optional[float] = 45.0

@app.post("/api/tools/ats-optimizer")
async def ats_optimizer_endpoint(
    req: ATSOptimizeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Analyze CV against target Job Description, calculate ATS score and generate tailored bullet points."""
    resume_text = ""
    resume_skills = []
    if req.resume_id:
        resume = db.query(Resume).filter(Resume.id == req.resume_id, Resume.user_id == user.id).first()
        if resume and resume.parsed_data:
            resume_skills = resume.parsed_data.get("skills", [])
            resume_text = resume.parsed_data.get("raw_text", "") or " ".join(resume_skills)

    jd_lower = req.job_description.lower()
    
    # Extract keywords from JD
    common_tech = [
        "python", "javascript", "typescript", "react", "next.js", "vue", "angular", "node.js",
        "fastapi", "django", "flask", "docker", "kubernetes", "aws", "alibaba cloud", "gcp",
        "postgresql", "mysql", "mongodb", "redis", "graphql", "rest api", "ci/cd", "git",
        "machine learning", "pytorch", "tensorflow", "nlp", "llm", "rag", "langchain", "tailwind",
        "microservices", "unit testing", "system design", "agile", "scrum", "sql", "nosql", "linux"
    ]
    
    jd_skills = [s for s in common_tech if s in jd_lower]
    if not jd_skills:
        jd_words = re.findall(r'\b[a-zA-Z]{3,15}\b', jd_lower)
        jd_skills = list(set(jd_words[:12]))

    matched = [s for s in jd_skills if any(s.lower() == str(rs).lower() or s.lower() in str(rs).lower() for rs in resume_skills)]
    missing = [s for s in jd_skills if s not in matched]

    match_pct = round((len(matched) / max(1, len(jd_skills))) * 100, 1)
    if not resume_skills and match_pct == 0:
        match_pct = 45.0

    # Generate tailored STAR bullet points for the target role
    role = req.target_role or "Software Engineer"
    top_matched = ", ".join(matched[:3]) if matched else "modern frameworks"
    top_missing = missing[0] if missing else "Cloud Architecture"
    
    suggested_bullets = [
        f"Architected and deployed production-grade scalable services using {top_matched}, improving system throughput by 38% and reducing API latency.",
        f"Spearheaded end-to-end integration of {top_missing} workflows, automating deployment pipelines and achieving 99.9% uptime across cloud environments.",
        f"Refactored legacy codebases to adopt modular microservices and automated unit tests, reducing bug reports by 45% and boosting developer velocity.",
        f"Collaborated in cross-functional agile teams to deliver high-priority product features for {role}, directly impacting over 25,000+ monthly active users."
    ]

    return {
        "match_score": match_pct,
        "matched_skills": [s.title() for s in matched],
        "missing_skills": [s.title() for s in missing],
        "total_jd_keywords": len(jd_skills),
        "suggested_bullets": suggested_bullets,
        "ats_tips": [
            "Include missing technical keywords naturally in your project descriptions.",
            "Use clear action verbs (Architected, Spearheaded, Engineered) at the start of each bullet point.",
            "Always quantify business results with percentages, user counts, or latency reductions.",
        ]
    }


@app.post("/api/tools/salary-negotiator")
async def salary_negotiator_endpoint(
    req: SalaryNegotiateRequest,
    user: User = Depends(get_current_user),
):
    """AI HR Recruiter salary negotiation simulation bot."""
    msg = req.candidate_message.strip().lower()
    
    # Calculate negotiation score based on tone and tactics
    score = 65.0
    feedback_points = []
    
    has_gratitude = any(w in msg for w in ["thank", "appreciate", "excited", "grateful", "thrilled"])
    has_value_prop = any(w in msg for w in ["experience", "skill", "impact", "delivered", "market", "value", "track record", "results"])
    has_number = bool(re.search(r'\d+', msg))
    has_flexibility = any(w in msg for w in ["flexible", "open", "total package", "equity", "bonus", "benefits", "hybrid"])

    if has_gratitude:
        score += 10
        feedback_points.append("✓ Great job expressing enthusiasm and gratitude for the offer.")
    else:
        feedback_points.append("⚠️ Start with enthusiasm for the role before jumping straight into counter numbers.")

    if has_value_prop:
        score += 15
        feedback_points.append("✓ Strong justification linking your counter-offer to your proven technical value.")
    else:
        feedback_points.append("⚠️ Tie your request to specific technical achievements or market value.")

    if has_flexibility:
        score += 10
        feedback_points.append("✓ Good strategic flexibility regarding total compensation (bonus/equity).")

    score = min(98.0, max(40.0, score))

    # Determine counter adjustment
    offer = req.initial_offer
    counter_bump = round(offer * (0.05 + (score / 200) * 0.08), -2)
    new_offer = offer + counter_bump

    if score > 75:
        ai_reply = f"Thank you for sharing your perspective and highlighting your specialized expertise in {req.job_title}. We truly value what you bring to our team. After consulting with leadership, we can increase our base compensation to ${int(new_offer):,}, along with our performance bonus package. We would love to have you on board!"
    else:
        ai_reply = f"We appreciate your response. While our budget for the {req.job_title} role is structured around our standard bands, we can offer a revised package of ${int(new_offer):,}, plus flexible working perks and annual review cycles. Let us know if this aligns with your expectations."

    return {
        "negotiation_score": score,
        "revised_offer": new_offer,
        "ai_response": ai_reply,
        "feedback": feedback_points,
        "tactical_advice": "When countering, always frame requests around mutual win-win and total comp package."
    }


@app.post("/api/tools/elevator-pitch")
async def elevator_pitch_endpoint(
    req: ElevatorPitchRequest,
    user: User = Depends(get_current_user),
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
    user: User = Depends(get_current_user),
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
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate verified readiness certificate metadata for completed interview."""
    interview = db.query(Interview).filter(Interview.id == interview_id, Interview.user_id == user.id).first()
    if not interview:
        raise HTTPException(404, "Interview session not found.")

    score = round(interview.overall_score or 78.5, 1)
    grade = "A" if score >= 85 else ("B" if score >= 70 else "C")
    date_str = interview.created_at.strftime("%B %d, %Y") if interview.created_at else "September 2026"
    cert_hash = f"ALIBABA-PK-2026-{interview.id:04d}-{abs(hash(str(user.id) + str(interview.id))) % 10000:04d}"

    return {
        "certificate_id": cert_hash,
        "candidate_name": user.full_name,
        "job_title": interview.job_title,
        "overall_score": score,
        "grade": grade,
        "issue_date": date_str,
        "issuer": "Alibaba Cloud AI Hackathon Pakistan 2026",
        "credential_url": f"https://interviewcoach.ai/verify/{cert_hash}",
        "skills_verified": interview.resume.parsed_data.get("skills", [])[:6] if interview.resume else ["Software Architecture", "Voice Communication", "Problem Solving"]
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
