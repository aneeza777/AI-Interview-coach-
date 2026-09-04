"""
Answer Evaluator Module
=======================
Evaluates the quality and relevance of interview answers using:
1. Fine-tuned sentence-transformers (semantic similarity to expected concepts)
2. Keyword matching (presence of expected terms)
3. Answer length/depth analysis
4. Combined scoring with detailed feedback
"""

import re
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple


# ──────────────────────────────────────────────
# Model loading (lazy singleton)
# ──────────────────────────────────────────────
_sentence_model = None
_TRAINED_MODEL_PATH = Path(__file__).parent.parent.parent / "training" / "models_output" / "answer_evaluator" / "final"


def get_sentence_model():
    """Load sentence-transformers model — fine-tuned if available, else base."""
    global _sentence_model
    if _sentence_model is None:
        from sentence_transformers import SentenceTransformer

        # Try fine-tuned model first
        if _TRAINED_MODEL_PATH.exists():
            try:
                print("[Answer Evaluator] Loading fine-tuned sentence-transformers model...")
                _sentence_model = SentenceTransformer(str(_TRAINED_MODEL_PATH))
                print("[Answer Evaluator] Fine-tuned model loaded successfully.")
                return _sentence_model
            except Exception as e:
                print(f"[Answer Evaluator] Failed to load fine-tuned model: {e}")

        # Fallback to base model
        print("[Answer Evaluator] Loading base sentence-transformers model...")
        _sentence_model = SentenceTransformer("all-MiniLM-L6-v2")
        print("[Answer Evaluator] Base model loaded.")
    return _sentence_model


# ──────────────────────────────────────────────
# Keyword matching score
# ──────────────────────────────────────────────
def _keyword_score(answer_text: str, expected_keywords: List[str]) -> Tuple[float, List[str]]:
    """
    Score based on how many expected keywords appear in the answer.

    Returns:
        (score 0-1, list of matched keywords)
    """
    if not expected_keywords:
        return 0.3, []  # No keywords to check — low neutral score

    answer_lower = answer_text.lower()
    matched = []

    for keyword in expected_keywords:
        keyword_lower = keyword.lower()
        # For short keywords, use word boundary matching
        if len(keyword_lower) <= 4:
            pattern = r'\b' + re.escape(keyword_lower) + r'\b'
            if re.search(pattern, answer_lower):
                matched.append(keyword)
        else:
            if keyword_lower in answer_lower:
                matched.append(keyword)

    if not expected_keywords:
        return 0.5, matched

    score = len(matched) / len(expected_keywords)
    return round(score, 3), matched


# ──────────────────────────────────────────────
# Semantic similarity score
# ──────────────────────────────────────────────
def _semantic_score(answer_text: str, question: str, expected_keywords: List[str]) -> float:
    """
    Score based on semantic similarity between the answer and
    a constructed "ideal answer" from question + keywords.
    """
    try:
        model = get_sentence_model()

        # Build a reference text from question + keywords
        reference = question + ". " + ". ".join(expected_keywords[:10])

        # Encode both texts
        answer_embedding = model.encode([answer_text])
        reference_embedding = model.encode([reference])

        # Cosine similarity
        similarity = np.dot(answer_embedding[0], reference_embedding[0]) / (
            np.linalg.norm(answer_embedding[0]) * np.linalg.norm(reference_embedding[0])
        )

        # Rescale to be more discriminating:
        # unrelated text (~0.05 sim) -> 0, clearly relevant (~0.6 sim) -> 1
        normalized = max(0.0, min(1.0, (similarity - 0.05) / 0.55))
        return round(float(normalized), 3)

    except Exception as e:
        print(f"[Answer Evaluator] Semantic scoring failed: {e}")
        return 0.3  # Fallback score


# ──────────────────────────────────────────────
# Answer depth/length score
# ──────────────────────────────────────────────
def _depth_score(answer_text: str) -> Tuple[float, Dict]:
    """
    Score based on answer length and structure.
    Good interview answers are typically 30-200 words.
    """
    words = answer_text.split()
    word_count = len(words)
    sentences = [s.strip() for s in re.split(r'[.!?]+', answer_text) if s.strip()]
    sentence_count = len(sentences)

    # Optimal range: 30-200 words
    if word_count < 10:
        length_score = 0.2  # Too short
        length_feedback = "Answer is too short — try to elaborate more."
    elif word_count < 30:
        length_score = 0.5
        length_feedback = "Answer could use more detail."
    elif word_count <= 200:
        length_score = 0.9
        length_feedback = "Good answer length."
    elif word_count <= 350:
        length_score = 0.7
        length_feedback = "Slightly long — try to be more concise."
    else:
        length_score = 0.5
        length_feedback = "Too long — focus on key points."

    # Sentence variety bonus
    variety_bonus = min(1.0, sentence_count / 5)

    combined = (length_score * 0.7) + (variety_bonus * 0.3)

    return round(combined, 3), {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "length_feedback": length_feedback,
    }


# ──────────────────────────────────────────────
# Filler word detection
# ──────────────────────────────────────────────
FILLER_WORDS = [
    "um", "uh", "like", "you know", "basically", "actually",
    "literally", "honestly", "i mean", "sort of", "kind of",
    "right", "so yeah", "yeah", "hmm", "ah",
]


def _count_fillers(answer_text: str) -> Tuple[int, List[str]]:
    """Count filler words in the answer."""
    answer_lower = answer_text.lower()
    found_fillers = []

    for filler in FILLER_WORDS:
        count = answer_lower.count(filler)
        if count > 0:
            found_fillers.extend([filler] * count)

    return len(found_fillers), found_fillers


# ──────────────────────────────────────────────
# Repetition detection
# ──────────────────────────────────────────────
def _repetition_penalty(answer_text: str) -> Tuple[float, float]:
    """
    Penalize answers that repeat the same words/phrases heavily.

    Returns:
        (penalty 0-0.4, unique_word_ratio 0-1)
    """
    words = re.findall(r"[a-z0-9']+", answer_text.lower())
    if len(words) < 6:
        return 0.0, 1.0  # too short to judge repetition

    unique_ratio = len(set(words)) / len(words)

    # Also count how often the most common word repeats
    from collections import Counter
    most_common_count = Counter(words).most_common(1)[0][1]
    repeat_ratio = most_common_count / len(words)

    if unique_ratio >= 0.72 and repeat_ratio < 0.15:
        return 0.0, round(unique_ratio, 3)
    elif unique_ratio >= 0.55:
        return 0.08, round(unique_ratio, 3)
    elif unique_ratio >= 0.40:
        return 0.18, round(unique_ratio, 3)
    else:
        # Very repetitive (same words over and over)
        return 0.35, round(unique_ratio, 3)


# ──────────────────────────────────────────────
# Main evaluation function
# ──────────────────────────────────────────────
def evaluate_answer(
    answer_text: str,
    question: str,
    expected_keywords: List[str],
    question_type: str = "general",
) -> Dict:
    """
    Evaluate an interview answer comprehensively.

    Args:
        answer_text: The transcribed answer text.
        question: The interview question that was asked.
        expected_keywords: List of keywords expected in a good answer.
        question_type: "technical" or "behavioral".

    Returns:
        {
            "content_score": float (0-100),
            "breakdown": {
                "keyword_score": float,
                "semantic_score": float,
                "depth_score": float,
                "matched_keywords": List[str],
                "missed_keywords": List[str],
                "word_count": int,
                "sentence_count": int,
                "filler_count": int,
            },
            "feedback": str,
            "tips": List[str],
        }
    """
    if not answer_text.strip():
        return {
            "content_score": 0,
            "breakdown": {
                "keyword_score": 0,
                "semantic_score": 0,
                "depth_score": 0,
                "matched_keywords": [],
                "missed_keywords": expected_keywords,
                "word_count": 0,
                "sentence_count": 0,
                "filler_count": 0,
            },
            "feedback": "No answer provided. Try speaking your response clearly.",
            "tips": ["Take a moment to think before answering.", "Even a brief answer is better than silence."],
        }

    # Run all scoring components
    kw_score, matched_kw = _keyword_score(answer_text, expected_keywords)
    sem_score = _semantic_score(answer_text, question, expected_keywords)
    dep_score, depth_info = _depth_score(answer_text)
    filler_count, fillers_found = _count_fillers(answer_text)
    rep_penalty, unique_ratio = _repetition_penalty(answer_text)

    # Missed keywords
    missed_kw = [kw for kw in expected_keywords if kw not in matched_kw]

    # ── Weighted combination ──
    # For technical: keywords matter more
    # For behavioral: depth and semantics matter more
    if question_type == "technical":
        weights = {"keyword": 0.40, "semantic": 0.30, "depth": 0.30}
    else:
        weights = {"keyword": 0.25, "semantic": 0.35, "depth": 0.40}

    raw_score = (
        kw_score * weights["keyword"]
        + sem_score * weights["semantic"]
        + dep_score * weights["depth"]
    )

    # Penalty for excessive fillers (max -15%) + repetition
    filler_penalty = min(0.15, filler_count * 0.02)
    final_score = max(0.0, raw_score - filler_penalty - rep_penalty)

    # Convert to 0-100 scale
    content_score = round(final_score * 100, 1)

    # ── Generate feedback ──
    feedback_parts = []
    tips = []

    if kw_score >= 0.7:
        feedback_parts.append("Great keyword coverage — you hit the key points.")
    elif kw_score >= 0.4:
        feedback_parts.append("Decent answer, but you missed some important concepts.")
        tips.append(f"Try to mention: {', '.join(missed_kw[:5])}")
    else:
        feedback_parts.append("Your answer didn't cover many expected topics.")
        tips.append(f"Focus on discussing: {', '.join(missed_kw[:5])}")
        tips.append("Relate your answer to your actual experience.")

    if sem_score >= 0.6:
        feedback_parts.append("Your answer is semantically relevant to the question.")
    elif sem_score >= 0.4:
        feedback_parts.append("Your answer is somewhat related but could be more focused.")
        tips.append("Stay closer to the question topic.")
    else:
        feedback_parts.append("Your answer seems off-topic. Try to address the question directly.")
        tips.append("Re-read the question and think about what the interviewer is really asking.")

    feedback_parts.append(depth_info["length_feedback"])

    if filler_count > 5:
        tips.append(f"You used {filler_count} filler words (um, uh, like). Try pausing instead.")
    elif filler_count > 2:
        tips.append(f"Watch out for filler words — you used {filler_count}. A brief pause works better.")

    if rep_penalty >= 0.18:
        feedback_parts.append("Your answer repeated the same words/phrases a lot, which lowers its impact.")
        tips.append("Avoid repeating the same sentence — add new points, examples, or details instead.")

    return {
        "content_score": content_score,
        "breakdown": {
            "keyword_score": round(kw_score * 100, 1),
            "semantic_score": round(sem_score * 100, 1),
            "depth_score": round(dep_score * 100, 1),
            "matched_keywords": matched_kw,
            "missed_keywords": missed_kw,
            "word_count": depth_info["word_count"],
            "sentence_count": depth_info["sentence_count"],
            "filler_count": filler_count,
            "unique_word_ratio": unique_ratio,
        },
        "feedback": " ".join(feedback_parts),
        "tips": tips,
    }


if __name__ == "__main__":
    # Quick test
    test_answer = (
        "I have three years of experience with Python and I've built several "
        "web applications using Django. I also have experience with REST APIs "
        "and database design using PostgreSQL. In my last project, I developed "
        "a microservices architecture that improved system performance by 40%."
    )

    result = evaluate_answer(
        answer_text=test_answer,
        question="Explain your experience with Python. What projects have you built using it?",
        expected_keywords=["python", "project", "built", "developed", "experience", "application", "web"],
        question_type="technical",
    )

    print(f"Content Score: {result['content_score']}/100")
    print(f"Feedback: {result['feedback']}")
    print(f"Tips: {result['tips']}")
    print(f"Breakdown: {result['breakdown']}")
