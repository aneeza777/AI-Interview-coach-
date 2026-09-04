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
        "Walk me through how you'd approach debugging a production issue under tight time constraints.",
        "What's your experience with code reviews, and how do you give constructive feedback to peers?",
        "How do you balance writing perfect, architecturally sound code with meeting strict product deadlines?",
        "Describe a situation where you had to refactor a legacy codebase. What strategy did you follow?",
        "How do you manage technical debt when developing features rapidly?",
    ],
    "web developer": [
        "What modern frontend frameworks and backend technologies are you most comfortable working with?",
        "How do you ensure your web applications are cross-browser compatible and responsive on mobile devices?",
        "Explain how you optimize website load speed, assets, and API requests for smooth user experience.",
        "How do you handle client-side form validation, error states, and security vulnerabilities like XSS or CSRF?",
        "Walk me through the lifecycle of an HTTP request from the browser address bar to the database and back.",
        "Tell me about a web application you built from scratch. What challenges did you encounter?",
    ],
    "frontend developer": [
        "How do you make sure your web applications are accessible (WCAG) and responsive across all viewports?",
        "Tell me about a time you had to profile and optimize frontend rendering performance.",
        "How do you manage state in complex frontend applications (e.g., Redux, Context, Zustand)?",
        "What's your approach to component-driven design, modular CSS, and reusable UI libraries?",
        "How do you handle asynchronous data fetching, loading skeletons, and optimistic UI updates?",
        "Explain the difference between Server-Side Rendering (SSR), Client-Side Rendering (CSR), and Static Site Generation.",
    ],
    "backend developer": [
        "How do you design RESTful or GraphQL APIs that are scalable, versioned, and easy to maintain?",
        "Explain your approach to relational vs non-relational database design, indexing, and query optimization.",
        "How do you handle authentication, role-based authorization, and token management in distributed backend systems?",
        "What caching strategies (e.g., Redis, Memcached) do you use to mitigate heavy traffic loads on databases?",
        "Describe a time you diagnosed and resolved a high-latency database bottleneck or deadlock in production.",
        "How do you structure microservices communication, message queues (RabbitMQ/Kafka), and error retries?",
    ],
    "full stack developer": [
        "How do you decide which business logic belongs on the client-side vs the server-side?",
        "Describe a full-stack project you built end-to-end from database schema design to responsive UI.",
        "How do you ensure data integrity and type safety between your frontend client and backend APIs?",
        "What is your continuous deployment (CI/CD) workflow and how do you manage environment configurations?",
        "How do you handle WebSocket or real-time event streaming in a full-stack architecture?",
    ],
    "data scientist": [
        "How do you validate that your machine learning model will generalize well on unseen test data?",
        "Explain your methodology for handling messy, skewed, or incomplete real-world datasets.",
        "How do you communicate complex technical and mathematical findings to non-technical business stakeholders?",
        "Tell me about a project where your exploratory data analysis directly led to a high-impact business decision.",
        "What metrics (Precision, Recall, ROC-AUC, F1) do you prioritize when evaluating imbalanced classification problems?",
    ],
    "machine learning engineer": [
        "How do you take an ML model from Jupyter notebook experimentation into a scalable production API?",
        "What model deployment, containerization, and low-latency inference challenges have you solved?",
        "How do you monitor model performance over time to detect data drift and concept drift in production?",
        "Explain your experience with advanced feature engineering, embeddings, and vector similarity search.",
        "How do you choose between fine-tuning a pre-trained Transformer model vs utilizing prompt engineering with RAG?",
    ],
    "mobile developer": [
        "How do you handle state management, memory leaks, and activity lifecycles in mobile applications?",
        "What is your architectural approach to building mobile apps that work seamlessly offline with local sync?",
        "How do you optimize mobile UI rendering, frame rates (60/120 fps), and battery consumption on diverse devices?",
        "Tell me about a challenging native integration or platform-specific mobile problem you solved.",
    ],
    "flutter developer": [
        "How do you manage complex application state in Flutter (e.g., Bloc, Riverpod, Provider)?",
        "What is your experience with platform channels and integrating native Android (Kotlin) / iOS (Swift) code?",
        "How do you handle responsive layouts and adaptive UI widgets across phones, tablets, and web?",
        "Tell me about a Flutter app you published and how you organized its clean layered architecture.",
    ],
    "devops engineer": [
        "Describe your ideal automated CI/CD pipeline from git push to zero-downtime production deployment.",
        "How do you approach Infrastructure as Code (IaC) using tools like Terraform, Ansible, or CloudFormation?",
        "What centralized logging, distributed tracing, and real-time alerting tools (e.g. Prometheus, Grafana) have you configured?",
        "How do you enforce security guardrails, secrets management, and container vulnerability scanning in cloud deployments?",
    ],
    "ui/ux designer": [
        "Walk me through your end-to-end design process from user research, wireframing, to high-fidelity prototypes in Figma.",
        "How do you conduct usability testing and incorporate feedback into iterative design sprints?",
        "Tell me about a time you had to defend a user-centric design decision against engineering or business constraints.",
        "How do you balance aesthetic visual appeal with strict accessibility standards (contrast, typography, screen readers)?",
    ],
    "default": [
        "What excites you most about this role and how does it fit into your long-term career goals?",
        "How does your previous technical and academic experience prepare you to succeed here?",
        "What do you consider your strongest professional quality, and what area are you actively working to improve?",
        "How do you approach receiving constructive criticism or code review feedback from team members?",
        "Describe a time you had to quickly learn a new technology or framework to complete a high-priority deliverable.",
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
        keywords = key.replace("/", " ").split()
        if any(kw in title_lower for kw in keywords):
            return key
    return "default"


def _paraphrase(template_q: Dict) -> str:
    """Pick a paraphrased version of a question."""
    if "paraphrases" in template_q and template_q["paraphrases"]:
        return random.choice(template_q["paraphrases"])
    return template_q["question"]


def _generate_cv_questions(resume_data: Dict, job_title: str, mode: str = "direct") -> List[Dict]:
    """Generate questions based on resume content with rich contextual awareness and random variety."""
    questions = []

    experience = resume_data.get("experience", {})
    companies = experience.get("companies", [])
    total_years = experience.get("total_years", 0) or 0
    company = _pick_valid_company(companies)
    projects = resume_data.get("projects", [])

    # 1. Experience-based questions
    if total_years > 0:
        exp_options = [
            f"I see you have {total_years}+ years of experience in the field. Could you walk me through your career progression and key milestones so far?",
            f"With around {total_years} years of professional background, what has been the most technically challenging problem you had to solve?",
            f"Reflecting on your {total_years}+ years in tech, how has your engineering approach and problem-solving mindset evolved over time?",
        ]
        questions.append({
            "question": random.choice(exp_options),
            "type": "experience",
            "expected_keywords": ["role", "company", "project", "responsibility", "learn", "growth", "experience", "milestone"],
            "difficulty": "medium" if mode == "direct" else "easy",
        })
    else:
        fresh_options = [
            "Could you tell me about your academic journey and any hands-on internship or coursework projects you've worked on?",
            "As an emerging technologist, what practical software engineering projects have you built that best demonstrate your technical passion?",
            "How do you approach learning complex programming frameworks independently outside of standard coursework?",
        ]
        questions.append({
            "question": random.choice(fresh_options),
            "type": "experience",
            "expected_keywords": ["education", "project", "internship", "learn", "hands-on", "experience", "coursework"],
            "difficulty": "easy",
        })

    if company:
        comp_options = [
            f"Tell me more about your responsibilities during your time at {company}. What were your primary contributions and achievements?",
            f"What was the most impactful feature or project you delivered while working at {company}?",
            f"How did you collaborate with cross-functional team members and senior engineers during your tenure at {company}?",
        ]
        questions.append({
            "question": random.choice(comp_options),
            "type": "experience",
            "expected_keywords": ["responsibility", "achieve", "result", "project", "team", "contribute", company.lower()],
            "difficulty": "medium",
        })

    # 2. Project-based questions
    if projects:
        best_project = projects[0][:50]
        proj_options = [
            f"I noticed your project '{best_project}'. Can you describe the system architecture, your individual role, and the main technical challenge you solved?",
            f"Regarding your project '{best_project}', what key design trade-offs did you make during implementation?",
            f"If you were to scale '{best_project}' to 100,000 active users, what architectural changes or caching layers would you introduce?",
        ]
        questions.append({
            "question": random.choice(proj_options),
            "type": "projects",
            "expected_keywords": ["project", "architecture", "build", "develop", "result", "challenge", "solution", "impact"],
            "difficulty": "hard" if mode == "direct" else "medium",
            "target_project": best_project,
        })
    elif resume_data.get("raw_text", "").lower().count("project") > 0:
        questions.append({
            "question": "Can you describe a technical project from your resume that you are particularly proud of, including the challenges you overcame?",
            "type": "projects",
            "expected_keywords": ["project", "proud", "build", "develop", "result", "learn", "challenge", "impact"],
            "difficulty": "medium",
        })

    # 3. Education-based questions
    education = resume_data.get("education", [])
    if education:
        edu_options = [
            "How has your academic background and coursework prepared you for the technical demands of this role?",
            "What was the most rewarding technical or software project you completed during your degree studies?",
        ]
        questions.append({
            "question": random.choice(edu_options),
            "type": "education",
            "expected_keywords": ["education", "university", "degree", "course", "skill", "prepare", "learn", "foundation"],
            "difficulty": "easy",
        })

    # 4. Skill-based questions
    skills = resume_data.get("skills", [])
    if skills:
        shuffled_skills = list(skills)
        random.shuffle(shuffled_skills)
        for skill in shuffled_skills[:3]:
            paraphrases = [
                f"Could you walk me through how you've used {skill} in a real-world project, and what challenges you solved with it?",
                f"How would you rate your hands-on proficiency in {skill}, and what architecture patterns have you applied using it?",
                f"What is a memorable feature or bug fix where {skill} played a crucial role in your implementation?",
                f"How do you handle error handling, performance optimization, and testing when building with {skill}?",
            ]
            questions.append({
                "question": random.choice(paraphrases),
                "type": "technical",
                "expected_keywords": [skill.lower(), "project", "experience", "use", "build", "develop", "implement"],
                "difficulty": "medium",
                "target_skill": skill,
            })

    # Shuffle non-intro CV questions for variety
    random.shuffle(questions)
    return questions


def _generate_job_questions(job_title: str, mode: str = "direct") -> List[Dict]:
    """Generate questions specific to the target job title with random sampling."""
    category = _match_job_title(job_title)
    templates = list(JOB_QUESTION_TEMPLATES.get(category, JOB_QUESTION_TEMPLATES["default"]))
    random.shuffle(templates)

    questions = []
    for q_text in templates:
        questions.append({
            "question": q_text,
            "type": "job_specific",
            "expected_keywords": ["experience", "approach", "project", "team", "problem", "solution", "architecture"],
            "difficulty": "hard" if mode == "direct" else "medium",
        })

    return questions


def _generate_follow_up(last_answer: str, last_question: Dict) -> Optional[Dict]:
    """Generate a simple follow-up question based on the previous answer."""
    answer_lower = last_answer.lower()

    # If they mentioned a technology, ask deeper
    tech_keywords = ["python", "react", "flutter", "django", "node", "aws", "docker", "machine learning", "sql", "javascript"]
    for tech in tech_keywords:
        if tech in answer_lower:
            return {
                "question": f"You mentioned {tech}. Could you go a bit deeper into how exactly you used it in your project?",
                "type": "follow_up",
                "expected_keywords": [tech, "use", "implement", "build", "example", "detail"],
                "difficulty": "medium",
            }

    # If answer is short, ask for elaboration
    words = last_answer.split()
    if len(words) < 25:
        return {
            "question": "Could you expand on that a bit more? I'd love to hear a specific technical example.",
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
    difficulty: str = "mid",  # "junior", "mid", "senior"
) -> List[Dict]:
    """
    Build a complete adaptive interview question plan.
    Ensures randomized, non-repetitive, and role-tailored questions.

    Args:
        resume_data: Parsed resume dict.
        job_title: Target job title.
        mode: 'practice' (more tips, easier pace) or 'direct' (formal mock interview).
        total_questions: Target number of questions (default 10).

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

    # 2. CV walkthrough questions (3-4 randomized questions)
    cv_questions = _generate_cv_questions(resume_data, job_title, mode=mode)
    plan.extend(cv_questions[:3])

    # 3. Behavioral questions (2-3 questions, sampled randomly)
    behavioral_sample = random.sample(BEHAVIORAL_QUESTIONS, min(3, len(BEHAVIORAL_QUESTIONS)))
    for b in behavioral_sample:
        plan.append({
            "question": _paraphrase(b),
            "type": b["type"],
            "expected_keywords": b["expected_keywords"],
            "difficulty": "hard" if mode == "direct" else b["difficulty"],
        })

    # 4. Job-specific questions (3 randomized questions)
    job_qs = _generate_job_questions(job_title, mode=mode)
    plan.extend(job_qs[:3])

    # 5. Closing (1 question)
    closing = random.choice(CLOSING_QUESTIONS)
    plan.append({
        "question": closing["question"],
        "type": closing["type"],
        "expected_keywords": closing["expected_keywords"],
        "difficulty": closing["difficulty"],
    })

    # Ensure exact question count
    if len(plan) > total_questions:
        if total_questions <= 2:
            plan = plan[:total_questions]
        else:
            # Keep intro (0) and closing (-1), trim from middle
            middle = plan[1:-1]
            random.shuffle(middle)
            plan = [plan[0]] + middle[:total_questions - 2] + [plan[-1]]

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


def _sanitize_education(education_val: Optional[str]) -> str:
    """Sanitize education string, stripping phone numbers, URLs, and noisy status text."""
    if not education_val or not isinstance(education_val, str):
        return "Computer Science"
    
    clean = education_val.strip()
    # Remove phone numbers, cell numbers, emails
    clean = re.sub(r'(?:cell|phone|tel|contact|mobile)\s*:\s*[\+\d\s\-\.\(\)]+', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '', clean)
    clean = re.sub(r'\+?\d[\d\s\-\.\(\)]{7,}\d', '', clean)
    # Remove trailing status like (final result awaited) with hands-
    clean = re.sub(r'\(.*?\)', '', clean)
    clean = re.sub(r'with\s+hands.*$', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\s+', ' ', clean).strip()

    # If common degrees appear, format cleanly
    clean_lower = clean.lower()
    if "computer science" in clean_lower:
        if "bs" in clean_lower or "bachelor" in clean_lower:
            return "BS Computer Science"
        return "Computer Science"
    elif "software engineering" in clean_lower:
        if "bs" in clean_lower or "bachelor" in clean_lower:
            return "BS Software Engineering"
        return "Software Engineering"
    elif "information technology" in clean_lower or "bsit" in clean_lower:
        return "Information Technology"
    elif "data science" in clean_lower:
        return "Data Science"
    elif "artificial intelligence" in clean_lower or "ai" in clean_lower.split():
        return "Artificial Intelligence"

    # If it's too short or contains no letters, fallback
    if len(clean) < 3 or not any(c.isalpha() for c in clean):
        return "Computer Science"

    return clean[:40]


def generate_model_answer(question: Dict, resume_data: Dict, job_title: str) -> str:
    """
    Generate a sample / model answer for a given interview question.
    Uses resume data and STAR methodology (Situation, Task, Action, Result)
    to provide high quality, contextual, and realistic responses.
    """
    q_type = question.get("type", "general")
    q_text = question.get("question", "").lower()
    name = _sanitize_name(resume_data.get("name"))
    skills = resume_data.get("skills", [])
    top_skills = ", ".join(skills[:3]) if skills else "modern software engineering practices and tools"
    primary_skill = question.get("target_skill") or (skills[0] if skills else "technical problem solving")
    
    education_list = resume_data.get("education", [])
    education = _sanitize_education(education_list[0] if education_list else None)
    
    experience = resume_data.get("experience", {})
    total_years = experience.get("total_years", 0) or 0
    company = _pick_valid_company(experience.get("companies", []))
    projects = resume_data.get("projects", [])
    target_proj = question.get("target_project") or (projects[0][:40] if projects else None)

    # 1. Introduction
    if q_type == "introduction":
        if total_years > 0:
            exp_phrase = f"with notable experience at {company}, " if company else ""
            return (
                f"Hello, my name is {name}. I hold a background in {education} and bring {total_years}+ years "
                f"of professional experience in the field, {exp_phrase}specializing in {top_skills}. "
                f"Throughout my career, I have focused on engineering scalable, high-performance systems and "
                f"collaborating across teams to deliver user-centric products. I am excited about this {job_title} "
                f"position because it directly aligns with my technical background and allows me to contribute to impactful initiatives."
            )
        else:
            return (
                f"Hello, my name is {name}. I graduated with a degree in {education}, where I built a strong "
                f"foundation in software engineering principles and computer science fundamentals. "
                f"Through intensive academic and hands-on projects, I have developed solid proficiency in {top_skills}. "
                f"I am eager to begin my career as a {job_title}, applying my problem-solving skills, curiosity, "
                f"and passion for clean code to make a positive impact on your team."
            )

    # 2. Experience-based (STAR method)
    if q_type == "experience":
        if company and total_years > 0:
            return (
                f"During my time at {company} (as part of my {total_years}+ years of experience), "
                f"I worked on core technical deliverables. [Situation & Task] Our team was tasked with building and "
                f"scaling reliable software components under fast-paced release cycles. [Action] I utilized {top_skills} "
                f"to design clean modular architectures, implement automated tests, and collaborate closely in daily agile sprints. "
                f"[Result] As a result, we enhanced overall system throughput, minimized post-release defects, and consistently "
                f"delivered major milestones on schedule."
            )
        elif total_years > 0:
            return (
                f"Over my {total_years}+ years of industry experience, I have developed and maintained several production-grade applications. "
                f"[Situation & Task] In a recent role, our primary challenge was optimizing delivery workflows and implementing key business features. "
                f"[Action] I applied {top_skills} to develop scalable modules, streamline API communication, and maintain strict code quality standards. "
                f"[Result] This approach led to smoother deployments, reduced latency, and positive feedback from stakeholders."
            )
        else:
            return (
                f"During my academic journey in {education}, I engaged in multiple comprehensive coursework and capstone projects. "
                f"[Situation & Task] Our objective was to architect and deliver real-world software solutions from scratch. "
                f"[Action] I took charge of the technical design using {top_skills}, establishing coding conventions, git workflows, and unit testing. "
                f"[Result] We successfully presented fully working prototypes on time, earning top academic evaluations and providing me with "
                f"practical, hands-on development experience."
            )

    # 3. Project-based (STAR method)
    if q_type == "projects":
        proj_name = f"'{target_proj}'" if target_proj else "a full-stack application"
        return (
            f"In my project {proj_name}, [Situation & Task] the goal was to build an efficient, user-friendly solution addressing a practical need. "
            f"[Action] I took ownership of the technical implementation using {top_skills}, structuring the database and backend logic, "
            f"integrating RESTful interfaces, and optimizing performance bottlenecks through systematic debugging. "
            f"[Result] The project successfully achieved high responsiveness and reliability, demonstrating my ability to manage the complete "
            f"software lifecycle from concept to deployment."
        )

    # 4. Technical / Skill-based
    if q_type == "technical":
        return (
            f"I have extensive hands-on experience utilizing {primary_skill} in real-world scenarios. "
            f"[Situation & Task] When implementing complex features, choosing the appropriate design patterns in {primary_skill} is essential for maintainability and performance. "
            f"[Action] I focus on writing modular, self-documenting code, enforcing type safety and automated testing, and following ecosystem best practices. "
            f"[Result] This disciplined approach ensures that components built with {primary_skill} remain robust, easily testable, and straightforward for the team to scale."
        )

    # 5. Behavioral (STAR method tailored to theme)
    if q_type == "behavioral":
        if any(w in q_text for w in ["conflict", "disagree", "teammate", "difficult"]):
            return (
                "[Situation] In a previous project, a teammate and I had differing opinions on technical architecture choices for a critical feature. "
                "[Task] Our objective was to reach a decision quickly without compromising product quality or team dynamics. "
                "[Action] I scheduled a dedicated discussion where we mapped both approaches against key metrics—scalability, delivery timeline, and maintenance cost. "
                "[Result] We synthesized the best aspects of both approaches into a unified plan, which delivered the feature on time and strengthened our collaboration."
            )
        elif any(w in q_text for w in ["mistake", "fail", "error", "wrong"]):
            return (
                "[Situation] Early in a major release, an edge-case validation bug reached the staging environment due to a missing boundary test. "
                "[Task] I took direct accountability for fixing the defect and ensuring it could not happen again. "
                "[Action] I promptly patched the validation logic, wrote exhaustive regression tests covering the edge cases, and updated our CI test suite. "
                "[Result] The patch passed validation seamlessly, and the improved automated test suite prevented similar edge-case regressions in subsequent sprints."
            )
        else:  # Deadline, pressure, challenge, or general behavioral
            return (
                "[Situation] During a critical release cycle, unexpected requirement changes compressed our delivery timeline significantly. "
                "[Task] I needed to ensure all essential functionalities were completed without sacrificing test coverage or code reliability. "
                "[Action] I prioritized the core deliverables, broke complex tasks into bite-sized milestones, and maintained transparent daily communication with the team. "
                "[Result] We delivered the release on schedule with zero high-severity production defects, proving the effectiveness of structured prioritization and clear communication."
            )

    # 6. Education
    if q_type == "education":
        return (
            f"My education in {education} gave me a comprehensive grounding in data structures, algorithms, and system design. "
            f"Beyond theory, I actively applied these principles through practical assignments using {top_skills}. "
            f"This academic foundation equipped me with the analytical mindset and problem-solving discipline required to succeed in a {job_title} role."
        )

    # 7. Job-specific
    if q_type == "job_specific":
        return (
            f"As a {job_title}, my core focus is on engineering clean, scalable, and maintainable solutions that directly support user needs. "
            f"When approaching a new problem, I start by clarifying requirements and edge cases, then design a modular architecture leveraging {top_skills}. "
            f"Throughout development, I emphasize automated testing, continuous integration, and clear documentation to ensure long-term stability."
        )

    # 8. Follow-up
    if q_type == "follow_up":
        return (
            f"To elaborate on that: when working with {primary_skill}, I pay close attention to architectural separation, exception handling, and performance trade-offs. "
            f"In practice, this means writing clean unit and integration tests, monitoring runtime metrics, and iterating based on real user feedback."
        )

    # 9. Closing
    if q_type == "closing":
        return (
            f"Thank you very much for this opportunity. I would love to learn more about the team's upcoming engineering priorities, "
            f"the tech stack roadmap, and what key milestones success would look like for a {job_title} in the first 90 days."
        )

    # Fallback
    return (
        f"For this question, I would structure my answer using the STAR method: outlining the Situation and Task, "
        f"explaining how I applied {top_skills} during the Action phase, and highlighting the measurable business Result."
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
