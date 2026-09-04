"""
Report Generator Module
=======================
Combines all scoring results into a comprehensive interview performance report.
Generates:
1. Per-question breakdown (content + confidence scores)
2. Overall performance score
3. Strengths and weaknesses analysis
4. Actionable improvement tips
"""

from typing import Dict, List
import numpy as np


# ──────────────────────────────────────────────
# Per-question result structure
# ──────────────────────────────────────────────
def compile_question_result(
    question: Dict,
    transcription: Dict,
    content_eval: Dict,
    confidence: Dict,
) -> Dict:
    """
    Combine all scores for a single question's answer.

    Args:
        question: The question dict (with number, text, type, difficulty).
        transcription: Output from speech_to_text.transcribe_audio().
        content_eval: Output from answer_evaluator.evaluate_answer().
        confidence: Output from confidence_detector.detect_confidence().

    Returns:
        Unified result dict for this question.
    """
    content_score = content_eval.get("content_score", 0)
    confidence_score = confidence.get("confidence_score", 0)

    # Weighted combined score: 60% content, 40% confidence
    combined_score = round(content_score * 0.6 + confidence_score * 0.4, 1)

    return {
        "question_number": question.get("number", 0),
        "question": question.get("question", ""),
        "question_type": question.get("type", "general"),
        "difficulty": question.get("difficulty", "medium"),
        "transcription": transcription.get("text", ""),
        "audio_duration": transcription.get("duration", 0),
        "content_score": content_score,
        "confidence_score": confidence_score,
        "combined_score": combined_score,
        "content_breakdown": content_eval.get("breakdown", {}),
        "confidence_breakdown": confidence.get("breakdown", {}),
        "content_feedback": content_eval.get("feedback", ""),
        "confidence_feedback": confidence.get("feedback", ""),
        "content_tips": content_eval.get("tips", []),
        "confidence_tips": confidence.get("tips", []),
    }


# ──────────────────────────────────────────────
# Overall report generation
# ──────────────────────────────────────────────
def generate_report(
    question_results: List[Dict],
    resume_data: Dict = None,
    job_title: str = "",
) -> Dict:
    """
    Generate the final comprehensive interview report.

    Args:
        question_results: List of per-question result dicts.
        resume_data: Original parsed resume data.
        job_title: Target job title.

    Returns:
        {
            "overall_score": float,
            "content_average": float,
            "confidence_average": float,
            "grade": str,
            "strengths": List[str],
            "weaknesses": List[str],
            "tips": List[str],
            "question_results": List[Dict],
            "summary": str,
        }
    """
    if not question_results:
        return {
            "overall_score": 0,
            "content_average": 0,
            "confidence_average": 0,
            "grade": "N/A",
            "strengths": [],
            "weaknesses": ["No questions answered yet."],
            "tips": ["Complete the interview to receive your report."],
            "question_results": [],
            "summary": "No data available.",
        }

    # ── Calculate averages ──
    content_scores = [r["content_score"] for r in question_results]
    confidence_scores = [r["confidence_score"] for r in question_results]
    combined_scores = [r["combined_score"] for r in question_results]

    content_avg = round(np.mean(content_scores), 1)
    confidence_avg = round(np.mean(confidence_scores), 1)
    overall_score = round(np.mean(combined_scores), 1)

    # ── Grade assignment ──
    if overall_score >= 85:
        grade = "A"
        grade_label = "Excellent"
    elif overall_score >= 70:
        grade = "B"
        grade_label = "Good"
    elif overall_score >= 55:
        grade = "C"
        grade_label = "Fair"
    elif overall_score >= 40:
        grade = "D"
        grade_label = "Needs Work"
    else:
        grade = "F"
        grade_label = "Significant Improvement Needed"

    # ── Identify strengths and weaknesses ──
    strengths = []
    weaknesses = []

    # Content strengths
    if content_avg >= 75:
        strengths.append("Strong content knowledge — your answers cover the key topics well.")
    elif content_avg >= 55:
        strengths.append("Decent answer quality — you understand the basics.")

    # Confidence strengths
    if confidence_avg >= 75:
        strengths.append("High speaking confidence — you sound professional and assured.")
    elif confidence_avg >= 55:
        strengths.append("Reasonable speaking confidence — your delivery is mostly clear.")

    # Per-category analysis
    tech_results = [r for r in question_results if r["question_type"] == "technical"]
    behav_results = [r for r in question_results if r["question_type"] == "behavioral"]

    if tech_results:
        tech_avg = np.mean([r["content_score"] for r in tech_results])
        if tech_avg >= 70:
            strengths.append(f"Good technical depth (avg: {tech_avg:.0f}/100).")
        elif tech_avg < 50:
            weaknesses.append(f"Technical answers need more depth (avg: {tech_avg:.0f}/100).")

    if behav_results:
        behav_avg = np.mean([r["content_score"] for r in behav_results])
        if behav_avg >= 70:
            strengths.append(f"Strong behavioral/soft-skill answers (avg: {behav_avg:.0f}/100).")
        elif behav_avg < 50:
            weaknesses.append(f"Behavioral answers could be more detailed (avg: {behav_avg:.0f}/100).")

    # Confidence-related weaknesses
    if confidence_avg < 50:
        weaknesses.append("Speaking confidence is low — practice speaking out loud regularly.")

    # Check for specific issues across all answers
    total_fillers = sum(
        r.get("content_breakdown", {}).get("filler_count", 0)
        for r in question_results
    )
    if total_fillers > 20:
        weaknesses.append(f"Excessive filler words detected ({total_fillers} total). Practice replacing 'um/uh' with pauses.")

    avg_wpm_values = [
        r.get("confidence_breakdown", {}).get("speaking_rate", {}).get("wpm", 0)
        for r in question_results
        if r.get("confidence_breakdown", {}).get("speaking_rate", {}).get("wpm", 0) > 0
    ]
    if avg_wpm_values:
        avg_wpm = np.mean(avg_wpm_values)
        if avg_wpm > 180:
            weaknesses.append(f"Speaking too fast (avg {avg_wpm:.0f} WPM). Aim for 120-160 WPM.")
        elif avg_wpm < 100:
            weaknesses.append(f"Speaking too slowly (avg {avg_wpm:.0f} WPM). Try to pick up the pace slightly.")

    # Ensure at least one strength
    if not strengths:
        strengths.append("You completed the interview — that's a great first step!")

    # ── Generate improvement tips ──
    tips = []

    if content_avg < 60:
        tips.append("Study common interview questions for your target role and practice structured answers (STAR method: Situation, Task, Action, Result).")
        tips.append("Review your resume and prepare specific examples for each skill/experience listed.")

    if confidence_avg < 60:
        tips.append("Practice speaking answers out loud in front of a mirror or record yourself.")
        tips.append("Before the interview, do deep breathing exercises to reduce nervousness.")

    if total_fillers > 10:
        tips.append("When you feel an 'um' or 'uh' coming, just pause silently instead. Short pauses sound thoughtful, not awkward.")

    tips.append("Record yourself answering each question and listen back — you'll spot areas to improve quickly.")
    tips.append("Prepare 3-5 stories from your experience that can be adapted to answer multiple questions.")

    if job_title:
        tips.append(f"Research common {job_title} interview questions and prepare thoughtful answers for each.")

    # ── Generate summary text ──
    summary_parts = [
        f"Overall Score: {overall_score}/100 (Grade: {grade} — {grade_label})",
        f"Content Quality: {content_avg}/100 | Speaking Confidence: {confidence_avg}/100",
    ]

    if strengths:
        summary_parts.append(f"Top Strength: {strengths[0]}")
    if weaknesses:
        summary_parts.append(f"Key Area to Improve: {weaknesses[0]}")

    summary = "\n".join(summary_parts)

    return {
        "overall_score": overall_score,
        "content_average": content_avg,
        "confidence_average": confidence_avg,
        "grade": grade,
        "grade_label": grade_label,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "tips": tips,
        "question_results": question_results,
        "summary": summary,
        "job_title": job_title,
        "total_questions": len(question_results),
    }


if __name__ == "__main__":
    # Quick test with mock data
    mock_results = [
        {
            "question_number": 1,
            "question": "Tell me about yourself.",
            "question_type": "behavioral",
            "difficulty": "easy",
            "content_score": 72,
            "confidence_score": 65,
            "combined_score": 69.2,
            "content_breakdown": {"filler_count": 3, "word_count": 85},
            "confidence_breakdown": {"speaking_rate": {"wpm": 145}},
            "content_feedback": "Good answer.",
            "confidence_feedback": "Decent confidence.",
        },
        {
            "question_number": 2,
            "question": "Explain your experience with Python.",
            "question_type": "technical",
            "difficulty": "medium",
            "content_score": 80,
            "confidence_score": 70,
            "combined_score": 76,
            "content_breakdown": {"filler_count": 1, "word_count": 120},
            "confidence_breakdown": {"speaking_rate": {"wpm": 138}},
            "content_feedback": "Strong technical answer.",
            "confidence_feedback": "Good pace.",
        },
    ]

    report = generate_report(mock_results, job_title="Software Engineer")
    print(report["summary"])
    print(f"\nStrengths: {report['strengths']}")
    print(f"Weaknesses: {report['weaknesses']}")
    print(f"Tips: {report['tips']}")
