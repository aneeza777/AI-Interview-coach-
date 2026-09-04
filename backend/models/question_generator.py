"""
Question Generator Module
==========================
Generates personalized interview questions based on:
1. Resume content (skills, experience, education)
2. Target job title

Uses fine-tuned FLAN-T5 model when available, combined with
template-based logic as fallback.
"""

import re
import random
from pathlib import Path
from typing import Dict, List, Tuple, Optional


# ──────────────────────────────────────────────
# Fine-tuned model loading
# ──────────────────────────────────────────────
_TRAINED_MODEL_PATH = Path(__file__).parent.parent.parent / "training" / "models_output" / "question_generator" / "final"
_qg_model = None
_qg_tokenizer = None


def _load_trained_model():
    """Load fine-tuned question generator if available."""
    global _qg_model, _qg_tokenizer

    if _qg_model is not None:
        return True  # Already loaded

    if not _TRAINED_MODEL_PATH.exists():
        return False

    try:
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        from peft import PeftModel

        print("[Question Generator] Loading fine-tuned model...")
        base_model = AutoModelForSeq2SeqLM.from_pretrained("google/flan-t5-small")
        _qg_model = PeftModel.from_pretrained(base_model, str(_TRAINED_MODEL_PATH))
        _qg_tokenizer = AutoTokenizer.from_pretrained(str(_TRAINED_MODEL_PATH))
        _qg_model.eval()
        print("[Question Generator] Fine-tuned model loaded successfully.")
        return True
    except Exception as e:
        print(f"[Question Generator] Could not load fine-tuned model: {e}")
        print("[Question Generator] Falling back to template-based generation.")
        return False


def _generate_with_model(context: str) -> Optional[str]:
    """Generate a question using the fine-tuned model."""
    if not _load_trained_model():
        return None

    try:
        input_text = f"Generate an interview question for: {context}"
        inputs = _qg_tokenizer(input_text, return_tensors="pt", max_length=256, truncation=True)
        outputs = _qg_model.generate(
            **inputs,
            max_length=128,
            num_beams=3,
            do_sample=True,
            temperature=0.8,
        )
        return _qg_tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
    except Exception as e:
        print(f"[Question Generator] Model generation failed: {e}")
        return None


# ──────────────────────────────────────────────
# Question Templates by Category
# ──────────────────────────────────────────────

# Behavioral / Soft-skill questions (always applicable)
BEHAVIORAL_QUESTIONS = [
    {
        "question": "Tell me about yourself and your background.",
        "type": "behavioral",
        "expected_keywords": ["experience", "education", "skills", "passion", "career", "background", "learn", "work"],
        "difficulty": "easy",
    },
    {
        "question": "Why are you interested in this position?",
        "type": "behavioral",
        "expected_keywords": ["opportunity", "growth", "skills", "team", "company", "role", "contribute", "learn"],
        "difficulty": "easy",
    },
    {
        "question": "Describe a challenging project you worked on and how you handled it.",
        "type": "behavioral",
        "expected_keywords": ["challenge", "problem", "solution", "team", "deadline", "result", "learned", "approach"],
        "difficulty": "medium",
    },
    {
        "question": "What are your greatest strengths and weaknesses?",
        "type": "behavioral",
        "expected_keywords": ["strength", "weakness", "improve", "skill", "teamwork", "communication", "working"],
        "difficulty": "easy",
    },
    {
        "question": "Where do you see yourself in 5 years?",
        "type": "behavioral",
        "expected_keywords": ["growth", "career", "learn", "goals", "develop", "future", "role", "lead"],
        "difficulty": "medium",
    },
    {
        "question": "Describe a time when you had to work under pressure or tight deadlines.",
        "type": "behavioral",
        "expected_keywords": ["pressure", "deadline", "manage", "prioritize", "deliver", "stress", "time", "result"],
        "difficulty": "medium",
    },
    {
        "question": "How do you handle conflicts or disagreements in a team?",
        "type": "behavioral",
        "expected_keywords": ["communication", "listen", "understand", "compromise", "respect", "resolve", "team", "perspective"],
        "difficulty": "medium",
    },
]

# Technical question templates (filled dynamically based on skills)
TECHNICAL_TEMPLATES = [
    {
        "template": "Explain your experience with {skill}. What projects have you built using it?",
        "expected_keywords_fn": lambda skill: [skill.lower(), "project", "built", "developed", "experience", "used", "application"],
        "difficulty": "medium",
    },
    {
        "template": "What are the key concepts of {skill} that every developer should know?",
        "expected_keywords_fn": lambda skill: [skill.lower(), "concept", "fundamental", "important", "understand", "principle", "core"],
        "difficulty": "medium",
    },
    {
        "template": "How would you explain {skill} to someone with no technical background?",
        "expected_keywords_fn": lambda skill: [skill.lower(), "simple", "explain", "tool", "use", "help", "build", "create"],
        "difficulty": "easy",
    },
    {
        "template": "What challenges have you faced while working with {skill} and how did you overcome them?",
        "expected_keywords_fn": lambda skill: [skill.lower(), "challenge", "problem", "solution", "debug", "fix", "learn", "approach"],
        "difficulty": "hard",
    },
    {
        "template": "Compare {skill} with its alternatives. When would you choose {skill} over other options?",
        "expected_keywords_fn": lambda skill: [skill.lower(), "compare", "alternative", "choose", "better", "advantage", "use case", "scenario"],
        "difficulty": "hard",
    },
]

# Job-title-specific question banks
JOB_SPECIFIC_QUESTIONS = {
    "software engineer": [
        {
            "question": "Describe your approach to writing clean, maintainable code.",
            "expected_keywords": ["clean", "readable", "maintainable", "comment", "naming", "structure", "test", "refactor"],
            "difficulty": "medium",
        },
        {
            "question": "How do you approach debugging a complex issue in production?",
            "expected_keywords": ["debug", "log", "monitor", "reproduce", "fix", "test", "deploy", "root cause"],
            "difficulty": "hard",
        },
        {
            "question": "Explain the software development lifecycle (SDLC) and your preferred methodology.",
            "expected_keywords": ["agile", "scrum", "waterfall", "sprint", "planning", "testing", "deployment", "requirement"],
            "difficulty": "medium",
        },
    ],
    "data scientist": [
        {
            "question": "How do you handle missing or corrupted data in a dataset?",
            "expected_keywords": ["missing", "impute", "drop", "clean", "outlier", "mean", "median", "analysis"],
            "difficulty": "medium",
        },
        {
            "question": "Explain the difference between supervised and unsupervised learning.",
            "expected_keywords": ["supervised", "unsupervised", "label", "classification", "regression", "clustering", "training"],
            "difficulty": "easy",
        },
        {
            "question": "How do you evaluate if a machine learning model is performing well?",
            "expected_keywords": ["accuracy", "precision", "recall", "f1", "cross-validation", "overfit", "metric", "test"],
            "difficulty": "medium",
        },
    ],
    "web developer": [
        {
            "question": "Explain the difference between client-side and server-side rendering.",
            "expected_keywords": ["client", "server", "render", "browser", "performance", "seo", "javascript", "html"],
            "difficulty": "medium",
        },
        {
            "question": "How do you ensure a website is responsive and works on all devices?",
            "expected_keywords": ["responsive", "media query", "flexbox", "grid", "mobile", "breakpoint", "test", "design"],
            "difficulty": "easy",
        },
        {
            "question": "What is REST API and how do you design one?",
            "expected_keywords": ["rest", "api", "endpoint", "http", "get", "post", "json", "status", "route"],
            "difficulty": "medium",
        },
    ],
    "frontend developer": [
        {
            "question": "How do you manage state in a large-scale frontend application?",
            "expected_keywords": ["state", "redux", "context", "hook", "prop", "store", "component", "global"],
            "difficulty": "hard",
        },
        {
            "question": "What performance optimization techniques do you use in frontend development?",
            "expected_keywords": ["lazy", "cache", "bundle", "minify", "image", "load", "render", "optimize"],
            "difficulty": "medium",
        },
    ],
    "backend developer": [
        {
            "question": "How do you design a scalable backend architecture?",
            "expected_keywords": ["scalable", "microservice", "database", "cache", "load balancer", "api", "server", "queue"],
            "difficulty": "hard",
        },
        {
            "question": "Explain database normalization and when you might denormalize.",
            "expected_keywords": ["normalization", "denormalize", "table", "relation", "performance", "redundancy", "query", "join"],
            "difficulty": "medium",
        },
    ],
    "devops engineer": [
        {
            "question": "Describe your CI/CD pipeline setup and best practices.",
            "expected_keywords": ["ci", "cd", "pipeline", "deploy", "build", "test", "automate", "jenkins", "github"],
            "difficulty": "medium",
        },
    ],
    "mobile developer": [
        {
            "question": "How do you handle app state and navigation in a mobile application?",
            "expected_keywords": ["state", "navigation", "screen", "route", "stack", "tab", "data", "persist"],
            "difficulty": "medium",
        },
    ],
    "ui/ux designer": [
        {
            "question": "Walk me through your design process from research to final delivery.",
            "expected_keywords": ["research", "wireframe", "prototype", "user", "test", "iterate", "feedback", "design"],
            "difficulty": "medium",
        },
    ],
}

# Default technical questions when job title doesn't match any specific category
DEFAULT_TECHNICAL_QUESTIONS = [
    {
        "question": "What technical skills do you consider your strongest, and why?",
        "expected_keywords": ["skill", "strong", "experience", "project", "proficient", "expert", "learn", "practice"],
        "difficulty": "easy",
    },
    {
        "question": "How do you stay updated with the latest trends in technology?",
        "expected_keywords": ["learn", "course", "blog", "community", "conference", "read", "practice", "trend"],
        "difficulty": "easy",
    },
    {
        "question": "Describe a technical problem you solved recently. What was your approach?",
        "expected_keywords": ["problem", "solution", "approach", "debug", "research", "implement", "test", "result"],
        "difficulty": "medium",
    },
]


# ──────────────────────────────────────────────
# Helper: match job title to category
# ──────────────────────────────────────────────
def _match_job_category(job_title: str) -> str:
    """Match a job title to one of the predefined categories."""
    title_lower = job_title.lower()

    category_map = {
        "software engineer": ["software engineer", "software developer", "sde", "swe"],
        "data scientist": ["data scientist", "data analyst", "ml engineer", "ai engineer", "machine learning"],
        "web developer": ["web developer", "full stack", "fullstack"],
        "frontend developer": ["frontend", "front-end", "ui developer"],
        "backend developer": ["backend", "back-end", "server"],
        "devops engineer": ["devops", "dev ops", "cloud engineer", "site reliability", "sre"],
        "mobile developer": ["mobile developer", "android", "ios", "flutter", "react native"],
        "ui/ux designer": ["ui/ux", "ux designer", "ui designer", "product designer"],
    }

    for category, keywords in category_map.items():
        for kw in keywords:
            if kw in title_lower:
                return category

    return "default"


# ──────────────────────────────────────────────
# Main question generation function
# ──────────────────────────────────────────────
def generate_questions(
    resume_data: Dict,
    job_title: str,
    num_questions: int = 10,
) -> List[Dict]:
    """
    Generate personalized interview questions.

    Args:
        resume_data: Parsed resume dict with skills, experience, education.
        job_title: Target job title string.
        num_questions: Total number of questions to generate (default 10).

    Returns:
        List of question dicts with: question, type, expected_keywords, difficulty.
    """
    questions = []
    skills = resume_data.get("skills", [])
    experience = resume_data.get("experience", {})

    # ── Step 1: Add 3-4 behavioral questions ──
    num_behavioral = min(4, num_questions // 3 + 1)
    selected_behavioral = random.sample(
        BEHAVIORAL_QUESTIONS, min(num_behavioral, len(BEHAVIORAL_QUESTIONS))
    )
    for q in selected_behavioral:
        questions.append({
            "question": q["question"],
            "type": "behavioral",
            "expected_keywords": q["expected_keywords"],
            "difficulty": q["difficulty"],
        })

    # ── Step 2: Add skill-based technical questions ──
    remaining_slots = num_questions - len(questions)
    if skills:
        # Pick top skills (max 4) for deep questions
        top_skills = skills[:4]
        skill_questions = []

        for skill in top_skills:
            template = random.choice(TECHNICAL_TEMPLATES)
            skill_questions.append({
                "question": template["template"].format(skill=skill),
                "type": "technical",
                "expected_keywords": template["expected_keywords_fn"](skill),
                "difficulty": template["difficulty"],
            })

        # Shuffle and take what we need
        random.shuffle(skill_questions)
        take_skill = min(len(skill_questions), remaining_slots // 2 + 1)
        questions.extend(skill_questions[:take_skill])

    # ── Step 2.5: Enhance with fine-tuned model (if available) ──
    if _load_trained_model() and skills:
        skill_context = f"Skills: {', '.join(skills[:6])}"
        model_questions = []
        for _ in range(3):  # Try to generate up to 3 model-based questions
            generated_q = _generate_with_model(skill_context)
            if generated_q and len(generated_q) > 15 and generated_q not in [q["question"] for q in questions]:
                model_questions.append({
                    "question": generated_q,
                    "type": "technical",
                    "expected_keywords": [s.lower() for s in skills[:3]] + ["explain", "experience", "project"],
                    "difficulty": "medium",
                })
        # Replace some template questions with model-generated ones
        if model_questions:
            replace_count = min(len(model_questions), len(questions) // 3)
            # Replace from the end of technical questions
            for mq in model_questions[:replace_count]:
                if len(questions) < num_questions:
                    questions.append(mq)

    # ── Step 3: Add job-title-specific questions ──
    remaining_slots = num_questions - len(questions)
    category = _match_job_category(job_title)

    if category != "default" and category in JOB_SPECIFIC_QUESTIONS:
        job_qs = JOB_SPECIFIC_QUESTIONS[category]
        take_job = min(len(job_qs), remaining_slots // 2 + 1)
        selected_job_qs = random.sample(job_qs, take_job)
        for q in selected_job_qs:
            questions.append({
                "question": q["question"],
                "type": "technical",
                "expected_keywords": q["expected_keywords"],
                "difficulty": q["difficulty"],
            })
    else:
        # Use default technical questions
        take_default = min(len(DEFAULT_TECHNICAL_QUESTIONS), remaining_slots // 2 + 1)
        for q in DEFAULT_TECHNICAL_QUESTIONS[:take_default]:
            questions.append({
                "question": q["question"],
                "type": "technical",
                "expected_keywords": q["expected_keywords"],
                "difficulty": q["difficulty"],
            })

    # ── Step 4: Fill remaining slots with more behavioral questions ──
    remaining_slots = num_questions - len(questions)
    if remaining_slots > 0:
        used_questions = {q["question"] for q in questions}
        unused_behavioral = [
            q for q in BEHAVIORAL_QUESTIONS
            if q["question"] not in used_questions
        ]
        for q in unused_behavioral[:remaining_slots]:
            questions.append({
                "question": q["question"],
                "type": "behavioral",
                "expected_keywords": q["expected_keywords"],
                "difficulty": q["difficulty"],
            })

    # ── Step 5: If still not enough, add generic questions ──
    remaining_slots = num_questions - len(questions)
    if remaining_slots > 0:
        fallback = [
            {
                "question": f"What interests you most about working as a {job_title}?",
                "type": "behavioral",
                "expected_keywords": ["interest", "passion", "role", "opportunity", "grow", "learn", "contribute"],
                "difficulty": "easy",
            },
            {
                "question": "Tell me about a project from your resume that you're most proud of.",
                "type": "behavioral",
                "expected_keywords": ["project", "proud", "achieve", "result", "build", "learn", "impact", "team"],
                "difficulty": "medium",
            },
        ]
        questions.extend(fallback[:remaining_slots])

    # Shuffle questions to mix behavioral and technical
    random.shuffle(questions)

    # Add question numbers
    for i, q in enumerate(questions):
        q["number"] = i + 1

    return questions[:num_questions]


if __name__ == "__main__":
    # Quick test
    sample_resume = {
        "name": "Ahmed Khan",
        "skills": ["Python", "React", "Django", "PostgreSQL", "Docker", "AWS"],
        "experience": {
            "job_titles": ["Software Engineer"],
            "companies": ["TechCorp"],
            "total_years": 2,
        },
        "education": ["BS Computer Science - FAST University"],
    }

    qs = generate_questions(sample_resume, "Full Stack Developer", num_questions=10)
    for q in qs:
        print(f"\nQ{q['number']} [{q['type']}] ({q['difficulty']}): {q['question']}")
        print(f"   Expected: {q['expected_keywords']}")
