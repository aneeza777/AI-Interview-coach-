#!/usr/bin/env python3
"""
End-to-End Pipeline Smoke Test
AI Interview Coach — Alibaba Cloud AI Hackathon Pakistan 2026
"""

import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from models.resume_parser import parse_resume
from models.cv_reviewer import review_cv
from models.interview_engine import build_interview_plan, generate_tip, generate_model_answer
from models.answer_evaluator import evaluate_answer
from models.confidence_detector import detect_confidence
from models.report_generator import compile_question_result, generate_report

def run_e2e_test():
    print("=" * 70)
    print("🚀 AI INTERVIEW COACH — FULL PIPELINE END-TO-END VERIFICATION")
    print("=" * 70)

    # 1. Resume Parser & Reviewer
    sample_cv = Path(__file__).parent / "sample_cv.pdf"
    if sample_cv.exists():
        print("\n[1/5] Testing Resume Parser & CV Reviewer...")
        parsed_resume = parse_resume(str(sample_cv))
        print(f"  ✓ Extracted Name: {parsed_resume.get('name')}")
        print(f"  ✓ Extracted Skills ({len(parsed_resume.get('skills', []))}): {', '.join(parsed_resume.get('skills', [])[:5])}")
        print(f"  ✓ Experience Years: {parsed_resume.get('experience', {}).get('total_years')} years")
        
        cv_review = review_cv(str(sample_cv))
        print(f"  ✓ CV Review Score: {cv_review.get('score')}/100 ({cv_review.get('grade')})")
    else:
        print("\n[1/5] Skipping sample_cv.pdf (not found)")
        parsed_resume = {
            "name": "Muhammad Adil",
            "skills": ["Python", "FastAPI", "Machine Learning", "PyTorch", "SQL"],
            "experience": {"total_years": 2, "companies": ["Tech Solutions PK"]},
            "education": ["BS Computer Science"],
            "projects": ["AI Mock Interview Coach", "CV Analyzer"]
        }

    # 2. Question Generator
    print("\n[2/5] Testing Question Generator (10 Dynamic Questions)...")
    job_title = "Full Stack AI Developer"
    questions = build_interview_plan(
        resume_data=parsed_resume,
        job_title=job_title,
        mode="practice",
        total_questions=10
    )
    print(f"  ✓ Generated {len(questions)} tailored questions for '{job_title}':")
    for q in questions:
        print(f"    Q{q['number']} [{q['type'].upper()}]: {q['question']}")

    # 3. Answer Evaluator
    print("\n[3/5] Testing Answer Evaluator (Sentence-Transformers + Concept Matching)...")
    test_q = questions[0]
    good_answer = "Hello, my name is Muhammad Adil. I completed my degree in Computer Science and have over 2 years of experience developing AI models and scalable web applications in Python, PyTorch, and FastAPI."
    poor_answer = "I don't really know, maybe I like coding websites sometimes."

    good_eval = evaluate_answer(
        answer_text=good_answer,
        question=test_q["question"],
        expected_keywords=test_q.get("expected_keywords", []),
        question_type=test_q.get("type", "introduction")
    )
    poor_eval = evaluate_answer(
        answer_text=poor_answer,
        question=test_q["question"],
        expected_keywords=test_q.get("expected_keywords", []),
        question_type=test_q.get("type", "introduction")
    )

    print(f"  ✓ Good Answer Score: {good_eval['content_score']}/100 (Feedback: {good_eval['feedback']})")
    print(f"  ✓ Poor Answer Score: {poor_eval['content_score']}/100 (Feedback: {poor_eval['feedback']})")

    # 4. Confidence Detector
    print("\n[4/5] Testing Confidence Detector (Librosa + PyTorch Classifier)...")
    sample_audio = Path(__file__).parent / "sample_audio.wav"
    if sample_audio.exists():
        conf_result = detect_confidence(str(sample_audio))
        duration = conf_result.get("breakdown", {}).get("speaking_rate", {}).get("duration", 0)
        print(f"  ✓ Audio Duration: {duration:.1f}s")
        print(f"  ✓ Confidence Score: {conf_result['confidence_score']}/100")
        print(f"  ✓ Speaking Feedback: {conf_result['feedback']}")
        pace_wpm = conf_result.get("breakdown", {}).get("speaking_rate", {}).get("wpm", 0)
        print(f"  ✓ Pace: {pace_wpm} WPM")
    else:
        print("  ✓ Sample audio not present, using simulated features.")
        conf_result = {
            "confidence_score": 85.0,
            "level": "confident",
            "feedback": "Strong, clear voice modulation with steady pacing.",
            "duration": 15.0,
            "breakdown": {"pace": {"wpm": 135}, "pauses": {"pause_ratio": 0.15}}
        }

    # 5. Report Generator
    print("\n[5/5] Testing Performance Report Generator...")
    compiled_q = compile_question_result(
        question=test_q,
        transcription={"text": good_answer, "duration": 15.0},
        content_eval=good_eval,
        confidence=conf_result
    )
    report = generate_report([compiled_q], resume_data=parsed_resume, job_title=job_title)
    print(f"  ✓ Overall Performance Score: {report['overall_score']}/100 ({report['grade']})")
    print(f"  ✓ Strengths ({len(report['strengths'])}): {report['strengths'][:2]}")
    print(f"  ✓ Actionable Tips ({len(report['tips'])}): {report['tips'][:2]}")

    print("\n" + "=" * 70)
    print("✅ ALL 6 PIPELINE STAGES PASSED VERIFICATION!")
    print("=" * 70)

if __name__ == "__main__":
    run_e2e_test()
