"""
Adaptive Interview Engine
==========================
Manages a realistic, human-like mock interview flow:
1. Starts with introductions
2. Walks through CV (experience, projects, education)
3. Dives into skills relevant to job title
4. Asks behavioral/situational questions
5. Asks job-specific questions
6. Provides real-time tips based on answer quality
7. Generates final report

Key features:
- Questions are paraphrased to avoid repetition
- Follow-up questions based on previous answers
- Two modes: "practice" (tips between questions) and "interview" (formal)
"""

import re
import random
from pathlib import Path
from typing import Dict, List, Optional


# ──────────────────────────────────────────────
# Interview stages
# ──────────────────────────────────────────────
INTRODUCTION_QUESTIONS = [
    {
        "question": "Could you please introduce yourself and give us a brief overview of your background?",
        "type": "introduction",
        "expected_keywords": ["name", "education", "experience", "skills", "background", "passion", "interested"],
        "difficulty": "easy",
    },
    {
        "question": "Tell us a little about who you are, your academic background, and what brings you to this interview today.",
        "type": "introduction",
        "expected_keywords": ["education", "experience", "skills", "background", "passion", "career", "learn"],
        "difficulty": "easy",
    },
]

# Paraphrased behavioral questions (same concept, different wording)
BEHAVIORAL_QUESTIONS = [
    {
        "question": "Can you share an example of a time you faced a tight deadline and how you managed it?",
        "paraphrases": [
            "Describe a situation where you had to deliver under significant time pressure.",
            "Walk me through how you've handled an urgent deadline in the past.",
            "Tell me about a moment when you were racing against the clock to finish something important.",
        ],
        "type": "behavioral",
        "expected_keywords": ["deadline", "pressure", "prioritize", "plan", "deliver", "time", "manage", "result"],
        "difficulty": "medium",
    },
    {
        "question": "Tell me about a conflict you had with a teammate and how you resolved it.",
        "paraphrases": [
            "Have you ever disagreed with a colleague on a project? How did you handle it?",
            "Describe a time when you had to navigate a disagreement within your team.",
            "How do you typically deal with interpersonal conflicts at work?",
        ],
        "type": "behavioral",
        "expected_keywords": ["conflict", "disagree", "team", "communicate", "listen", "understand", "resolve", "respect"],
        "difficulty": "medium",
    },
    {
        "question": "Describe a difficult problem you solved and what you learned from it.",
        "paraphrases": [
            "What's the toughest challenge you've overcome in a project?",
            "Tell me about a complex issue you tackled and how you approached it.",
            "Can you walk me through a problem that really pushed you to think critically?",
        ],
        "type": "behavioral",
        "expected_keywords": ["challenge", "problem", "solution", "approach", "learn", "result", "critical", "resolve"],
        "difficulty": "medium",
    },
    {
        "question": "Where do you see yourself professionally in the next few years?",
        "paraphrases": [
            "What are your career goals looking ahead?",
            "How do you envision your professional growth in the coming years?",
            "What direction do you hope your career takes from here?",
        ],
        "type": "behavioral",
        "expected_keywords": ["growth", "career", "goals", "learn", "develop", "future", "role", "lead"],
        "difficulty": "easy",
    },
    {
        "question": "How do you stay updated with the latest trends and technologies in your field?",
        "paraphrases": [
            "What do you do to keep your skills current in a fast-changing industry?",
            "How do you make sure you're continuously learning?",
            "What resources or communities do you rely on to stay sharp technically?",
        ],
        "type": "behavioral",
        "expected_keywords": ["learn", "course", "blog", "community", "conference", "read", "practice", "trend", "update"],
        "difficulty": "easy",
    },
]

# Closing questions
CLOSING_QUESTIONS = [
    {
        "question": "What questions do you have for us about the role or the company?",
        "type": "closing",
        "expected_keywords": ["role", "team", "company", "culture", "project", "growth", "learn", "opportunity"],
        "difficulty": "easy",
    },
    {
        "question": "Before we wrap up, is there anything else you'd like us to know about you?",
        "type": "closing",
        "expected_keywords": ["experience", "skill", "project", "strength", "passion", "contribute", "value"],
        "difficulty": "easy",
    },
]

# Job-specific question templates
JOB_QUESTION_TEMPLATES = {
    "software engineer": [
        "How do you ensure the code you write is clean, maintainable, and testable?",
        "Walk me through how you'd approach debugging a production issue.",
        "What's your experience with code reviews, and how do you give constructive feedback?",
        "How do you balance writing perfect code with meeting deadlines?",
    ],
    "frontend developer": [
        "How do you make sure your web applications are accessible and responsive?",
        "Tell me about a time you had to optimize frontend performance.",
        "How do you manage state in complex frontend applications?",
        "What's your approach to component design and reusability?",
    ],
    "backend developer": [
        "How do you design APIs that are scalable and easy to maintain?",
        "Explain your approach to database design and optimization.",
        "How do you handle authentication and security in backend systems?",
        "What strategies do you use for handling high traffic loads?",
    ],
    "full stack developer": [
        "How do you decide which logic belongs on the frontend vs the backend?",
        "Describe a full project you built from database to UI.",
        "How do you ensure consistency between frontend and backend APIs?",
        "What's your deployment and DevOps experience like?",
    ],
    "data scientist": [
        "How do you validate that your model will perform well on unseen data?",
        "Explain how you handle messy or incomplete datasets.",
        "How do you communicate technical findings to non-technical stakeholders?",
        "Tell me about a project where your analysis led to a business decision.",
    ],
    "machine learning engineer": [
        "How do you take a model from experimentation to production?",
        "What ML deployment challenges have you faced?",
        "How do you monitor model performance over time?",
        "Explain your experience with feature engineering.",
    ],
    "mobile developer": [
        "How do you handle app state and lifecycle in mobile development?",
        "What's your approach to building apps that work offline?",
        "How do you ensure your app performs well on different devices?",
        "Tell me about a challenging mobile UI problem you solved.",
    ],
    "flutter developer": [
        "How do you manage state in Flutter applications?",
        "What's your experience with platform channels and native integrations?",
        "How do you handle responsive layouts across different screen sizes?",
        "Tell me about a Flutter app you built and the architecture you used.",
    ],
    "devops engineer": [
        "Describe your ideal CI/CD pipeline.",
        "How do you approach infrastructure as code?",
        "What monitoring and alerting tools have you used?",
        "How do you handle security in cloud deployments?",
    ],
    "ui/ux designer": [
        "Walk me through your design process from research to final prototype.",
        "How do you incorporate user feedback into your designs?",
        "Tell me about a time you had to defend a design decision.",
        "How do you balance aesthetics with usability?",
    ],
    "default": [
        "What excites you most about this role?",
        "How would your previous experience help you succeed here?",
        "What do you consider your strongest professional quality?",
        "How do you handle feedback and criticism?",
    ],
}


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
def _match_job_title(job_title: str) -> str:
    """Match user job title to our templates."""
    title_lower = job_title.lower()
    for key in JOB_QUESTION_TEMPLATES:
        if key == "default":
            continue
        if any(kw in title_lower for kw in key.replace("/", " ").split()):
            return key
    return "default"


def _paraphrase(template_q: Dict) -> str:
    """Pick a paraphrased version of a question."""
    if "paraphrases" in template_q and template_q["paraphrases"]:
        return random.choice(template_q["paraphrases"])
    return template_q["question"]


def _generate_cv_questions(resume_data: Dict, job_title: str) -> List[Dict]:
    """Generate questions based on resume content."""
    questions = []

    # Experience-based questions
    experience = resume_data.get("experience", {})
    companies = experience.get("companies", [])
    total_years = experience.get("total_years", 0)

    if total_years > 0:
        questions.append({
            "question": f"I see you have {total_years}+ years of experience. Could you walk me through your career journey so far?",
            "type": "experience",
            "expected_keywords": ["role", "company", "project", "responsibility", "learn", "growth", "experience"],
            "difficulty": "easy",
        })

    # Use validated company name (filters out phone numbers, emails, etc)
    company = _pick_valid_company(companies)
    if company:
        questions.append({
            "question": f"Tell me more about your time at {company}. What were you responsible for, and what did you achieve?",
            "type": "experience",
            "expected_keywords": ["responsibility", "achieve", "result", "project", "team", "contribute", company.lower()],
            "difficulty": "medium",
        })

    # Project-based questions
    if resume_data.get("projects") or resume_data.get("raw_text", "").lower().count("project") > 0:
        questions.append({
            "question": "Can you describe a project from your resume that you're particularly proud of?",
            "type": "projects",
            "expected_keywords": ["project", "proud", "build", "develop", "result", "learn", "challenge", "impact"],
            "difficulty": "medium",
        })

    # Education-based questions
    education = resume_data.get("education", [])
    if education:
        questions.append({
            "question": "How has your education prepared you for this role?",
            "type": "education",
            "expected_keywords": ["education", "university", "degree", "course", "skill", "prepare", "learn", "foundation"],
            "difficulty": "easy",
        })

    # Skill-based questions
    skills = resume_data.get("skills", [])
    if skills:
        top_skills = skills[:3]
        for skill in top_skills:
            paraphrases = [
                f"Could you tell me about your experience working with {skill}?",
                f"How would you rate your proficiency in {skill}, and where have you used it?",
                f"What's a project where {skill} played a major role?",
                f"Walk me through how you'd solve a typical problem using {skill}.",
            ]
            questions.append({
                "question": random.choice(paraphrases),
                "type": "technical",
                "expected_keywords": [skill.lower(), "project", "experience", "use", "build", "develop"],
                "difficulty": "medium",
            })

    return questions


def _generate_job_questions(job_title: str) -> List[Dict]:
    """Generate questions specific to the target job title."""
    category = _match_job_title(job_title)
    templates = JOB_QUESTION_TEMPLATES.get(category, JOB_QUESTION_TEMPLATES["default"])

    questions = []
    for q_text in templates:
        questions.append({
            "question": q_text,
            "type": "job_specific",
            "expected_keywords": ["experience", "approach", "project", "team", "problem", "solution"],
            "difficulty": "medium",
        })

    return questions


def _generate_follow_up(last_answer: str, last_question: Dict) -> Optional[Dict]:
    """Generate a simple follow-up question based on the previous answer."""
    answer_lower = last_answer.lower()

    # If they mentioned a technology, ask deeper
    tech_keywords = ["python", "react", "flutter", "django", "node", "aws", "docker", "machine learning", "sql"]
    for tech in tech_keywords:
        if tech in answer_lower:
            return {
                "question": f"You mentioned {tech}. Could you go a bit deeper into how exactly you used it?",
                "type": "follow_up",
                "expected_keywords": [tech, "use", "implement", "build", "example", "detail"],
                "difficulty": "medium",
            }

    # If answer is short, ask for elaboration
    words = last_answer.split()
    if len(words) < 25:
        return {
            "question": "Could you expand on that a bit more? I'd love to hear the details.",
            "type": "follow_up",
            "expected_keywords": ["detail", "example", "explain", "expand", "more"],
            "difficulty": "easy",
        }

    return None


# ──────────────────────────────────────────────
# Generate the full interview plan
# ──────────────────────────────────────────────
def build_interview_plan(
    resume_data: Dict,
    job_title: str,
    mode: str = "direct",  # "practice" or "direct"
    total_questions: int = 10,
) -> List[Dict]:
    """
    Build a complete adaptive interview question plan.

    Args:
        resume_data: Parsed resume dict.
        job_title: Target job title.
        mode: 'practice' (more tips, easier pace) or 'direct' (formal interview).
        total_questions: Approximate number of questions.

    Returns:
        List of question dicts with metadata.
    """
    plan = []

    # 1. Introduction (1 question)
    intro = random.choice(INTRODUCTION_QUESTIONS)
    plan.append({
        "question": intro["question"],
        "type": intro["type"],
        "expected_keywords": intro["expected_keywords"],
        "difficulty": intro["difficulty"],
    })

    # 2. CV walkthrough questions (3-4 questions)
    cv_questions = _generate_cv_questions(resume_data, job_title)
    plan.extend(cv_questions[:4])

    # 3. Behavioral questions (2-3 questions, paraphrased)
    behavioral = random.sample(BEHAVIORAL_QUESTIONS, min(3, len(BEHAVIORAL_QUESTIONS)))
    for b in behavioral:
        plan.append({
            "question": _paraphrase(b),
            "type": b["type"],
            "expected_keywords": b["expected_keywords"],
            "difficulty": b["difficulty"],
        })

    # 4. Job-specific questions (2-3 questions)
    job_qs = _generate_job_questions(job_title)
    plan.extend(job_qs[:3])

    # 5. Closing (1 question)
    closing = random.choice(CLOSING_QUESTIONS)
    plan.append({
        "question": closing["question"],
        "type": closing["type"],
        "expected_keywords": closing["expected_keywords"],
        "difficulty": closing["difficulty"],
    })

    # Trim or extend to target count
    if len(plan) > total_questions:
        plan = plan[:total_questions]

    # Assign question numbers
    for i, q in enumerate(plan):
        q["number"] = i + 1

    return plan


# ──────────────────────────────────────────────
# Real-time tips generator
# ──────────────────────────────────────────────
def generate_tip(
    content_eval: Dict,
    confidence: Dict,
    mode: str = "practice",
) -> Optional[str]:
    """
    Generate a contextual tip during practice mode.
    In direct mode, tips are suppressed to simulate real interview.
    """
    if mode == "direct":
        return None

    content_score = content_eval.get("content_score", 0)
    confidence_score = confidence.get("confidence_score", 0)

    tips = []

    # Content tips
    if content_score < 40:
        tips.append("💡 Try to structure your answer with a clear beginning, middle, and end.")
    elif content_score < 60:
        tips.append("💡 Good start! Try adding a specific example or metric to strengthen your answer.")

    filler_count = content_eval.get("breakdown", {}).get("filler_count", 0)
    if filler_count > 3:
        tips.append("💡 You're using filler words. Replace 'um' with a brief pause — it sounds more confident.")

    # Confidence tips
    if confidence_score < 45:
        tips.append("💡 You sound nervous. Take a deep breath and speak a bit slower.")
    elif confidence_score < 65:
        tips.append("💡 Good energy! Try varying your tone to sound more engaging.")

    wpm = confidence.get("breakdown", {}).get("speaking_rate", {}).get("wpm", 0)
    if wpm > 180:
        tips.append("💡 You're speaking quite fast. Slowing down will help clarity.")
    elif wpm < 90:
        tips.append("💡 Try speaking a bit faster to keep the interviewer's attention.")

    if tips:
        return random.choice(tips)
    return "💡 Nice answer! Keep this confidence going."


# ──────────────────────────────────────────────
# Follow-up logic for dynamic interviews
# ──────────────────────────────────────────────
def maybe_add_follow_up(
    current_plan: List[Dict],
    last_answer: str,
    last_question: Dict,
    max_questions: int = 15,
) -> List[Dict]:
    """Dynamically insert a follow-up question if appropriate."""
    if len(current_plan) >= max_questions:
        return current_plan

    follow_up = _generate_follow_up(last_answer, last_question)
    if follow_up:
        follow_up["number"] = len(current_plan) + 1
        follow_up["is_follow_up"] = True
        current_plan.append(follow_up)

        # Renumber
        for i, q in enumerate(current_plan):
            q["number"] = i + 1

    return current_plan


# ──────────────────────────────────────────────
# Model answer generator (for practice mode)
# ──────────────────────────────────────────────
_NON_COMPANY_WORDS = {
    "engineer", "developer", "programmer", "manager", "analyst", "consultant",
    "architect", "designer", "intern", "lead", "director", "officer",
    "specialist", "associate", "coordinator", "founder", "head", "ceo",
    "cto", "cfo", "president", "vice", "senior", "junior", "chief",
    "software", "data", "web", "mobile", "front", "back", "full",
    "freelance", "self", "employed", "remote", "contract",
    "university", "college", "institute", "school", "academy", "education",
    "degree", "bachelor", "master", "phd", "diploma", "bs", "ms", "mba",
    "science", "engineering", "technology", "arts", "department", "student",
    "experience", "skills", "projects", "summary", "profile", "objective",
}


def _pick_valid_company(companies: List) -> Optional[str]:
    """
    Return the first company name that looks like a real organization.
    Filters out job titles, education terms, contact info, and other non-company text.
    """
    for c in companies or []:
        if not c or not isinstance(c, str):
            continue
        
        c_stripped = c.strip()
        c_lower = c_stripped.lower()
        
        # Reject contact info patterns (phone, email, etc)
        if '@' in c_lower or 'email' in c_lower:
            continue
        if any(pattern in c_lower for pattern in ['+92', '+1', '+91', 'contact', 'phone', 'mobile', 'tel', 'address']):
            continue
        # Reject if looks like a phone number (has 3+ consecutive digits)
        if re.search(r'\d{3,}', c_stripped):
            continue
        # Reject pure numbers
        if c_stripped.replace('-', '').replace('.', '').isdigit():
            continue
        
        words = [w for w in c_lower.split() if w.isalpha()]
        if not words:
            continue
        
        # Check if any word is a non-company word (job title, education, section header)
        if any(w in _NON_COMPANY_WORDS for w in words):
            continue
        
        # Must have multiple characters to be a company (avoid single letters)
        if len(c_stripped) < 2:
            continue
        
        # Too many words is suspicious
        if len(words) > 4:
            continue
            
        return c_stripped
    return None


def _sanitize_name(name: Optional[str]) -> str:
    """
    Sanitize a name field. Reject contact info and URLs.
    Returns a valid name or fallback to 'the candidate'.
    """
    if not name or not isinstance(name, str):
        return "the candidate"
    
    name_stripped = name.strip()
    name_lower = name_stripped.lower()
    
    # Reject URLs and web addresses
    if '://' in name_lower or 'www.' in name_lower:
        return "the candidate"
    if 'github.com' in name_lower or 'linkedin.com' in name_lower:
        return "the candidate"
    if 'facebook.com' in name_lower or 'twitter.com' in name_lower:
        return "the candidate"
    if '.com' in name_lower or '.io' in name_lower or '.co' in name_lower:
        return "the candidate"
    if re.search(r'[a-z0-9]+\.[a-z]{2,}', name_lower):
        return "the candidate"
    if '/' in name_stripped or '\\' in name_stripped:
        return "the candidate"
    
    # Reject contact info
    if '@' in name_lower or 'email' in name_lower:
        return "the candidate"
    if any(pattern in name_lower for pattern in ['+92', '+1', '+91', 'contact', 'phone', 'mobile', 'tel']):
        return "the candidate"
    # Reject if looks like a phone number
    if re.search(r'[\d\-\.]+\d{3,}', name_lower):
        return "the candidate"
    
    # Reject if mostly numbers/special chars
    alpha_ratio = sum(1 for c in name_stripped if c.isalpha()) / len(name_stripped) if name_stripped else 0
    if alpha_ratio < 0.6:
        return "the candidate"
    
    # Must have reasonable length
    if len(name_stripped) < 2 or len(name_stripped) > 100:
        return "the candidate"
    
    return name_stripped
    # Reject if very short or very long
    if len(name_stripped) < 2 or len(name_stripped) > 100:
        return "the candidate"
    
    return name_stripped


def generate_model_answer(question: Dict, resume_data: Dict, job_title: str) -> str:
    """
    Generate a sample / model answer for a given interview question.
    Uses resume data to personalize the answer.
    Sanitizes all inputs to prevent malformed answers.
    """
    q_type = question.get("type", "general")
    name = _sanitize_name(resume_data.get("name"))
    skills = resume_data.get("skills", [])
    top_skills = ", ".join(skills[:3]) if skills else "relevant technical skills"
    education_list = resume_data.get("education", [])
    education = education_list[0] if education_list else "my degree"
    experience = resume_data.get("experience", {})
    total_years = experience.get("total_years", 0) or 0
    company = _pick_valid_company(experience.get("companies", []))

    if q_type == "introduction":
        exp_phrase = f"including work at {company}. " if company else ""
        return (
            f"Hello, my name is {name}. I recently completed {education}. "
            f"I have around {total_years} years of experience, {exp_phrase}"
            f"and my core skills include {top_skills}. "
            f"I am excited about this {job_title} role because it lets me use these skills "
            f"to build products that make a real impact."
        )

    if q_type == "experience":
        if company:
            return (
                f"At {company}, I spent about {total_years} years working on meaningful projects. "
                f"My responsibilities included developing features, debugging issues, and collaborating with the team. "
                f"For example, I used {top_skills} to deliver a feature that improved the product. "
                f"This experience taught me how to balance quality with deadlines."
            )
        return (
            f"Over the last {total_years} years I have worked on meaningful projects in a professional setting. "
            f"My responsibilities included developing features, debugging issues, and collaborating with the team. "
            f"For example, I used {top_skills} to deliver a feature that improved the product. "
            f"This experience taught me how to balance quality with deadlines."
        )

    if q_type == "projects":
        return (
            f"One project I am proud of involved {top_skills}. I handled the implementation from planning to deployment, "
            f"faced real-world constraints, and delivered a working solution. "
            f"It strengthened my problem-solving skills and showed me the value of user feedback."
        )

    if q_type == "education":
        return (
            f"My time at {education} gave me a strong foundation in problem-solving and software development. "
            f"I also completed practical projects using {top_skills}, which prepared me well for a {job_title} role."
        )

    if q_type == "technical":
        return (
            f"I have hands-on experience with {top_skills}. In my recent work, I used them to build features, "
            f"fix bugs, and optimize performance. I also keep learning through personal projects and online courses."
        )

    if q_type == "behavioral":
        return (
            "In my previous role, I once faced a tight deadline on an important feature. "
            "I broke the task into smaller pieces, prioritized the critical parts, and communicated daily with the team. "
            "We delivered on time, and I learned the value of planning and transparent communication."
        )

    if q_type == "job_specific":
        return (
            f"As a {job_title}, I focus on writing clean, maintainable code and working closely with the team. "
            f"For any task, I start by understanding the requirements, then design a simple solution, "
            f"and finally test it thoroughly before deployment."
        )

    if q_type == "closing":
        return (
            "Thank you for the opportunity. I'd love to learn more about the team structure, "
            "the current projects, and what success looks like in this role in the first 90 days."
        )

    # Fallback for any other question type
    return (
        f"For this question, I would focus on my experience with {top_skills}, "
        f"give a specific example, and connect it clearly to the {job_title} role."
    )


if __name__ == "__main__":
    sample_resume = {
        "name": "Ahmed Khan",
        "skills": ["Python", "React", "Flutter", "Django", "PostgreSQL"],
        "experience": {"companies": ["TechCorp"], "total_years": 2},
        "education": ["BS Computer Science"],
    }

    plan = build_interview_plan(sample_resume, "Flutter Developer", mode="practice", total_questions=12)
    for q in plan:
        print(f"\nQ{q['number']} [{q['type']}] ({q['difficulty']}): {q['question']}")
        print(f"Model answer: {generate_model_answer(q, sample_resume, 'Flutter Developer')}")
