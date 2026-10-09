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

# Universal Job-specific question templates across all industries
JOB_QUESTION_TEMPLATES = {
    # ── 1. Technology & Software Engineering ──
    "software engineer": [
        "How do you ensure the code you write is clean, maintainable, and thoroughly tested?",
        "Walk me through how you'd approach debugging a critical production issue under tight time constraints.",
        "What's your experience with code reviews, and how do you give constructive feedback to peers?",
        "How do you balance writing architecturally sound code with meeting strict product deadlines?",
        "Describe a situation where you had to refactor a complex codebase. What strategy did you follow?",
        "How do you manage technical debt when developing features rapidly?",
    ],
    "web developer": [
        "What modern frontend frameworks and backend technologies are you most comfortable working with?",
        "How do you ensure your web applications are cross-browser compatible and responsive on all devices?",
        "Explain how you optimize website load speed, assets, and API requests for smooth user experience.",
        "How do you handle client-side form validation, error states, and security vulnerabilities like XSS or CSRF?",
        "Walk me through the lifecycle of an HTTP request from browser entry to database response.",
    ],
    "frontend developer": [
        "How do you make sure your web applications are accessible (WCAG) and responsive across all viewports?",
        "Tell me about a time you had to profile and optimize frontend rendering performance.",
        "How do you manage state in complex frontend applications (e.g., Redux, Context, Zustand)?",
        "What's your approach to component-driven design, modular styling, and reusable UI design systems?",
    ],
    "backend developer": [
        "How do you design RESTful or GraphQL APIs that are scalable, versioned, and easy to maintain?",
        "Explain your approach to database schema design, indexing strategies, and query optimization.",
        "How do you handle authentication, role-based authorization, and token management in distributed backend systems?",
        "What caching strategies (e.g., Redis) and message queues do you use to mitigate heavy traffic loads?",
    ],
    "data scientist": [
        "How do you validate that your machine learning model will generalize well on unseen test data?",
        "Explain your methodology for handling messy, skewed, or incomplete real-world datasets.",
        "How do you communicate complex statistical findings and data insights to non-technical business stakeholders?",
        "What metrics (Precision, Recall, ROC-AUC, F1) do you prioritize when evaluating imbalanced classification problems?",
    ],
    "mobile developer": [
        "How do you handle state management, memory leaks, and activity lifecycles in mobile applications?",
        "What is your architectural approach to building mobile apps that work seamlessly offline with local sync?",
        "How do you optimize mobile UI rendering, frame rates, and battery consumption on diverse devices?",
    ],
    "devops engineer": [
        "Describe your automated CI/CD pipeline from code commit to zero-downtime production deployment.",
        "How do you approach Infrastructure as Code (IaC) using tools like Terraform, Ansible, or CloudFormation?",
        "What centralized logging, distributed tracing, and real-time alerting systems have you configured?",
    ],
    "ui/ux designer": [
        "Walk me through your end-to-end design process from user research, wireframing, to high-fidelity prototypes.",
        "How do you conduct usability testing and incorporate feedback into iterative design sprints?",
        "Tell me about a time you had to defend a user-centric design decision against business constraints.",
    ],

    # ── 2. Healthcare, Medicine & Pharmaceuticals ──
    "healthcare": [
        "How do you ensure patient safety and clinical quality when managing high-acuity or emergency situations?",
        "Describe your approach to comprehensive diagnostic assessment and evidence-based treatment planning.",
        "How do you handle difficult conversations with patients and families regarding care plans or adverse outcomes?",
        "What protocols do you follow for medication administration, infection control, and accurate EHR documentation?",
        "Tell me about a time you collaborated with an interdisciplinary healthcare team to optimize patient outcomes.",
    ],

    # ── 3. Finance, Banking, Accounting & Audit ──
    "finance": [
        "Walk me through your methodology for financial modeling, valuation, and sensitivity analysis.",
        "How do you ensure strict compliance with GAAP/IFRS standards, tax laws, and regulatory reporting requirements?",
        "Describe a time you detected a critical discrepancy or financial risk during an audit or forecasting cycle.",
        "How do you communicate complex financial metrics, variances, and P&L statements to executive leadership?",
        "What strategies do you use for working capital optimization, cash flow management, and cost containment?",
    ],

    # ── 4. Engineering (Mechanical, Civil, Electrical, Industrial) ──
    "mechanical engineer": [
        "Walk me through your engineering design process from initial CAD modeling to physical prototyping and testing.",
        "How do you conduct Finite Element Analysis (FEA) and stress testing to ensure component structural integrity?",
        "Describe a situation where a design failed quality control or manufacturing tolerances and how you redesigned it.",
        "How do you apply Lean Manufacturing and Six Sigma principles to streamline production and eliminate bottlenecks?",
    ],
    "civil engineer": [
        "How do you approach structural analysis, load calculations, and building code compliance on major projects?",
        "Describe your process for managing on-site contractors, safety protocols, and construction timelines.",
        "Tell me about a geotechnical, environmental, or zoning constraint you encountered on a job site and how you resolved it.",
        "How do you coordinate architectural blueprints, structural drawings, and MEP requirements using AutoCAD/BIM?",
    ],
    "electrical engineer": [
        "How do you design, simulate, and debug complex circuit schematics and PCB layouts?",
        "What is your approach to power distribution, signal integrity, and electromagnetic interference (EMI) mitigation?",
        "Describe your experience with embedded microcontrollers, firmware testing, or industrial PLC automation.",
        "Walk me through a safety-critical electrical testing procedure you managed and the standards you applied.",
    ],

    # ── 5. Marketing, Advertising, PR & Content ──
    "marketing": [
        "How do you develop an end-to-end digital marketing strategy across SEO, paid channels, and content marketing?",
        "What key performance indicators (CAC, ROAS, LTV, conversion rate) do you prioritize when analyzing campaign ROI?",
        "Describe a successful campaign you planned and executed that significantly boosted brand awareness or revenue growth.",
        "How do you conduct customer persona research and A/B test messaging to optimize conversion funnels?",
    ],

    # ── 6. Sales & Business Development ──
    "sales": [
        "Walk me through your end-to-end sales cycle from prospecting high-value leads to contract closing.",
        "How do you handle tough price objections and negotiate terms while protecting company profitability?",
        "Describe a challenging enterprise client negotiation where you successfully built long-term trust.",
        "What pipeline management and CRM strategies do you use to consistently exceed sales targets?",
    ],

    # ── 7. Human Resources (HR) & Talent Acquisition ──
    "human resources": [
        "How do you source, evaluate, and attract top-tier talent in highly competitive employment markets?",
        "Describe a time you navigated a complex employee relations dispute or workplace grievance with empathy and fairness.",
        "How do you design performance management systems that align employee growth with company goals?",
        "What strategies do you use to foster workplace retention, engagement, and a high-performance organizational culture?",
    ],

    # ── 8. Legal, Law & Compliance ──
    "legal": [
        "How do you approach drafting and negotiating high-value commercial contracts to minimize corporate liability?",
        "Describe your process for conducting thorough legal due diligence during corporate transactions or audits.",
        "Tell me about a complex regulatory compliance challenge you solved under shifting statutory guidelines.",
        "How do you translate complex legal precedents and statutory risks into clear, actionable advice for business leaders?",
    ],

    # ── 9. Education, Teaching & Academia ──
    "education": [
        "How do you differentiate instruction to engage learners with diverse backgrounds, styles, and skill levels?",
        "Describe your philosophy on classroom management, learner assessment, and fostering critical thinking.",
        "Tell me about a curriculum or lesson plan you designed that produced measurable gains in student performance.",
        "How do you leverage modern educational technology and feedback loops to continuously enhance learning outcomes?",
    ],

    # ── 10. Supply Chain, Logistics & Operations ──
    "supply chain": [
        "How do you manage supplier relationships, lead times, and global supply chain disruptions?",
        "What inventory management and demand forecasting models do you use to prevent stockouts while minimizing holding costs?",
        "Describe a time you negotiated vendor contracts that delivered significant cost savings without sacrificing quality.",
        "How do you optimize warehouse throughput, logistics routes, and distribution network efficiency?",
    ],

    # ── 11. Graphic Design & Creative Arts ──
    "graphic designer": [
        "Walk me through your creative process from initial brief and moodboards to final multi-platform production assets.",
        "How do you balance brand consistency with fresh, innovative visual storytelling across digital and print media?",
        "Tell me about a time a client or stakeholder rejected your creative concept and how you iterated to a winning solution.",
        "How do you optimize visual hierarchy, typography, and color theory for maximum audience engagement?",
    ],

    # ── 12. Project & Product Management ──
    "project manager": [
        "How do you prioritize competing stakeholder demands and product roadmap features when resources are limited?",
        "Describe a project where unexpected scope creep threatened the launch deadline. How did you realign the team?",
        "What agile metrics and workflow rituals do you rely on to maintain high velocity and clear team accountability?",
        "How do you measure project success and conduct post-launch retrospectives to continuously improve execution?",
    ],

    # ── 13. Universal Domain-Agnostic Fallback (Applies to ANY Profession) ──
    "default": [
        "What core methodologies, industry standards, and best practices do you rely on most in your field?",
        "Walk me through a complex, high-stakes project or case you managed from inception to successful completion.",
        "How do you handle unforeseen roadblocks, tight deadlines, or shifting requirements in your work?",
        "What metrics or objective standards do you use to evaluate the quality and tangible impact of your work?",
        "How do you stay abreast of emerging research, regulatory changes, and advanced techniques in your industry?",
    ],
}


# ──────────────────────────────────────────────
# Multi-Domain Job Title Matcher
# ──────────────────────────────────────────────
def _match_job_title(job_title: str) -> str:
    """Intelligently match user job title to domain categories across all industries."""
    title_lower = job_title.lower()

    # Domain keyword associations
    domain_mappings = [
        # Healthcare & Medicine
        (["doctor", "physician", "surgeon", "nurse", "nursing", "medical", "pharmacist", "pharmacy", "dentist", "clinical", "hospital", "healthcare", "therapist"], "healthcare"),
        # Finance, Banking & Accounting
        (["finance", "financial", "accountant", "accounting", "auditor", "audit", "banker", "banking", "tax", "actuary", "cfa", "acca", "ca", "treasury"], "finance"),
        # Civil Engineering & Architecture
        (["civil", "structural", "construction", "site engineer", "surveyor", "architect", "architecture"], "civil engineer"),
        # Mechanical Engineering
        (["mechanical", "automotive", "hvac", "cad designer", "aerospace", "manufacturing engineer", "thermal"], "mechanical engineer"),
        # Electrical Engineering
        (["electrical", "electronics", "circuit", "power engineer", "telecom", "hardware engineer"], "electrical engineer"),
        # Marketing & Brand
        (["marketing", "seo", "sem", "social media", "content", "copywriter", "brand", "growth", "advertising", "pr"], "marketing"),
        # Sales & Business Dev
        (["sales", "business development", "account executive", "client relationship", "commercial", "tele-sales"], "sales"),
        # Human Resources
        (["hr", "human resources", "recruiter", "recruitment", "talent acquisition", "people operations"], "human resources"),
        # Legal & Compliance
        (["lawyer", "attorney", "legal", "compliance", "counsel", "paralegal", "advocate", "regulatory"], "legal"),
        # Education & Teaching
        (["teacher", "professor", "lecturer", "educator", "instructor", "academic", "principal", "curriculum"], "education"),
        # Supply Chain & Logistics
        (["supply chain", "logistics", "procurement", "inventory", "warehouse", "operations", "import", "export"], "supply chain"),
        # Graphic Design & Creative
        (["graphic", "designer", "illustrator", "animator", "video editor", "creative", "artist"], "graphic designer"),
        # Project & Product Management
        (["project manager", "product manager", "scrum master", "agile coach", "program manager"], "project manager"),
        # Tech & Data
        (["frontend", "front-end", "react", "vue", "angular"], "frontend developer"),
        (["backend", "back-end", "api", "database", "node", "django"], "backend developer"),
        (["data scientist", "data analyst", "bi analyst", "analytics"], "data scientist"),
        (["mobile", "android", "ios", "flutter", "react native"], "mobile developer"),
        (["devops", "cloud", "sre", "infrastructure", "system admin"], "devops engineer"),
        (["ui", "ux", "ui/ux", "product designer"], "ui/ux designer"),
        (["web developer", "full stack", "software engineer", "developer", "programmer", "coder"], "software engineer"),
    ]

    for keywords, category in domain_mappings:
        if any(re.search(rf"(?<![a-z]){re.escape(kw)}(?![a-z])", title_lower) for kw in keywords):
            return category

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
            f"With around {total_years} years of professional background, what has been the most challenging problem or case you had to solve in your work?",
            f"Reflecting on your {total_years}+ years of professional background, how has your strategic approach and problem-solving methodology evolved over time?",
        ]
        questions.append({
            "question": random.choice(exp_options),
            "type": "experience",
            "expected_keywords": ["role", "company", "project", "responsibility", "learn", "growth", "experience", "milestone"],
            "difficulty": "medium" if mode == "direct" else "easy",
        })
    else:
        fresh_options = [
            "Could you tell me about your academic journey and any hands-on internship, research, or coursework initiatives you've completed?",
            "As an emerging professional, what practical projects or case studies have you executed that best demonstrate your core capabilities?",
            "How do you approach mastering complex new methodologies, tools, or industry standards independently?",
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
            f"What was the most impactful initiative or project you delivered while working at {company}?",
            f"How did you collaborate with multidisciplinary team members and leadership during your tenure at {company}?",
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
            f"I noticed your project or initiative '{best_project}'. Can you describe your individual role, methodology, and the main challenge you solved?",
            f"Regarding your project '{best_project}', what key strategic trade-offs or design decisions did you make during execution?",
            f"If you were to expand '{best_project}' to a larger scale, what key optimizations or enhancements would you introduce?",
        ]
        questions.append({
            "question": random.choice(proj_options),
            "type": "projects",
            "expected_keywords": ["project", "methodology", "build", "deliver", "result", "challenge", "solution", "impact"],
            "difficulty": "hard" if mode == "direct" else "medium",
            "target_project": best_project,
        })
    elif resume_data.get("raw_text", "").lower().count("project") > 0:
        questions.append({
            "question": "Can you describe a key project or case study from your resume that you are particularly proud of, including the challenges you overcame?",
            "type": "projects",
            "expected_keywords": ["project", "proud", "build", "develop", "result", "learn", "challenge", "impact"],
            "difficulty": "medium",
        })

    # 3. Education-based questions
    education = resume_data.get("education", [])
    if education:
        edu_options = [
            "How has your academic background, degree, and training prepared you for the professional demands of this role?",
            "What was the most rewarding project, research, or coursework you completed during your academic education?",
        ]
        questions.append({
            "question": random.choice(edu_options),
            "type": "education",
            "expected_keywords": ["education", "university", "degree", "course", "skill", "prepare", "learn", "foundation"],
            "difficulty": "easy",
        })

    # 4. Skill-based questions (Universal across all fields)
    skills = resume_data.get("skills", [])
    if skills:
        shuffled_skills = list(skills)
        random.shuffle(shuffled_skills)
        for skill in shuffled_skills[:3]:
            paraphrases = [
                f"Could you walk me through how you've applied your expertise in {skill} in a real-world scenario, and what results you achieved with it?",
                f"How would you rate your hands-on proficiency in {skill}, and what best practices or standards do you follow when utilizing it?",
                f"Can you share a memorable challenge or case where your mastery of {skill} played a crucial role in achieving success?",
                f"How do you ensure quality, compliance, and optimal outcomes when working with {skill}?",
            ]
            questions.append({
                "question": random.choice(paraphrases),
                "type": "technical",
                "expected_keywords": [skill.lower(), "project", "experience", "use", "apply", "result", "implement"],
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
    """Sanitize education string (any discipline), stripping phone numbers, URLs, and noisy status text."""
    if not education_val or not isinstance(education_val, str):
        return "my field of study"

    clean = education_val.strip()
    # Remove phone numbers, cell numbers, emails
    clean = re.sub(r'(?:cell|phone|tel|contact|mobile)\s*:\s*[\+\d\s\-\.\(\)]+', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '', clean)
    clean = re.sub(r'\+?\d[\d\s\-\.\(\)]{7,}\d', '', clean)
    # Remove trailing status like (final result awaited) with hands-
    clean = re.sub(r'\(.*?\)', '', clean)
    clean = re.sub(r'with\s+hands.*$', '', clean, flags=re.IGNORECASE)
    # Remove year ranges / CGPA noise
    clean = re.sub(r'\b(19|20)\d{2}\b\s*[-–]?\s*((19|20)\d{2}|present)?', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'(cgpa|gpa)\s*[:\-]?\s*[\d\.\/]+', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\s+', ' ', clean).strip(" ,|-–")

    # If it's too short or contains no letters, fallback (domain-neutral)
    if len(clean) < 3 or not any(c.isalpha() for c in clean):
        return "my field of study"

    return clean[:60]


def generate_model_answer(question: Dict, resume_data: Dict, job_title: str) -> str:
    """
    Generate a sample / model answer for a given interview question.
    Uses resume data and STAR methodology (Situation, Task, Action, Result)
    to provide high quality, contextual, and realistic responses.

    100% domain-agnostic: wording is driven by the candidate's own CV data
    (skills, education, companies, projects) and the target job title, so it
    works for doctors, accountants, engineers, marketers, teachers, lawyers,
    developers, etc. without any field-specific hardcoding.
    """
    q_type = question.get("type", "general")
    q_text = question.get("question", "").lower()
    name = _sanitize_name(resume_data.get("name"))
    skills = resume_data.get("skills", [])
    top_skills = ", ".join(skills[:3]) if skills else f"the core competencies required of a {job_title}"
    primary_skill = question.get("target_skill") or (skills[0] if skills else f"core {job_title} responsibilities")

    education_list = resume_data.get("education", [])
    education = _sanitize_education(education_list[0] if education_list else None)

    experience = resume_data.get("experience", {})
    total_years = experience.get("total_years", 0) or 0
    company = _pick_valid_company(experience.get("companies", []))
    projects = resume_data.get("projects", [])
    target_proj = question.get("target_project") or (projects[0][:40] if projects else None)

    # 0. Check domain category for job title
    domain = _match_job_title(job_title)

    # 1. Introduction & Background (handles introduction type or question text)
    is_intro = q_type == "introduction" or any(w in q_text for w in [
        "introduce yourself", "tell me about yourself", "tell us about yourself",
        "your background", "overview of your background", "who you are", "walk me through your resume"
    ])
    if is_intro:
        if domain == "education":
            return (
                f"Hello, my name is {name}. With a strong passion for education and student-centered learning, "
                f"I bring experience in lesson planning, classroom management, differentiated instruction, and curriculum development. "
                f"Throughout my teaching practice, I focus on creating inclusive, engaging learning environments where every student can "
                f"achieve their full academic potential. I am excited about this {job_title} opportunity because it aligns directly with my "
                f"educational philosophy and dedication to student success."
            )
        elif domain in ["software engineer", "frontend developer", "backend developer", "mobile developer", "devops engineer", "data scientist"]:
            return (
                f"Hello, my name is {name}. I am a software engineer specializing in scalable system design, clean architecture, "
                f"and modern development best practices. Throughout my projects, I focus on building reliable, maintainable codebases "
                f"and collaborating closely with cross-functional teams to deliver high-impact software solutions. I am excited about this {job_title} "
                f"role because it allows me to contribute my technical problem-solving capabilities to your product roadmap."
            )
        elif domain == "healthcare":
            return (
                f"Hello, my name is {name}. I am a dedicated healthcare professional with comprehensive clinical background in patient "
                f"assessment, evidence-based care protocols, and empathetic communication. My core focus is always patient safety, accurate "
                f"clinical workflows, and collaborative interdisciplinary teamwork. I am enthusiastic about this {job_title} opportunity to deliver "
                f"high-quality compassionate care."
            )
        elif domain == "finance":
            return (
                f"Hello, my name is {name}. I am a finance and accounting professional with proven experience in financial modeling, "
                f"statutory compliance, budget forecasting, and risk analysis. I specialize in turning complex financial data into actionable "
                f"strategic insights that safeguard capital and drive profitability. I am excited to bring my analytical rigor to this {job_title} position."
            )
        elif domain in ["marketing", "sales"]:
            return (
                f"Hello, my name is {name}. I am a results-driven professional with extensive experience across strategic campaign planning, "
                f"data-driven conversion optimization, and client relationship management. In my work, I combine data-backed analytics with creative "
                f"execution to grow audience reach and maximize return on investment. I look forward to contributing to your commercial growth as a {job_title}."
            )
        else:
            if total_years > 0:
                exp_phrase = f"with notable experience at {company}, " if company else ""
                return (
                    f"Hello, my name is {name}. I hold a background in {education} and bring {total_years}+ years of professional experience "
                    f"in the field, {exp_phrase}specializing in {top_skills}. Throughout my career, I have focused on delivering high-quality, "
                    f"measurable outcomes and collaborating closely with colleagues and stakeholders. I am excited about this {job_title} position "
                    f"because it directly aligns with my expertise and allows me to contribute to impactful work."
                )
            return (
                f"Hello, my name is {name}. I completed my studies in {education}, where I built a strong foundation in the core principles of my discipline. "
                f"Through academic work, practical training, and hands-on assignments, I have developed solid proficiency in {top_skills}. "
                f"I am eager to begin my career as a {job_title}, applying my problem-solving ability, curiosity, and commitment to quality to make a positive impact on your team."
            )

    # 2. Tool & Daily Workflow questions
    if any(w in q_text for w in ["tools", "methodologies", "daily workflow", "languages", "technologies you use"]):
        if domain == "education":
            return (
                "In my daily instructional workflow, I integrate modern learning management systems (like Google Classroom or Canvas), "
                "interactive visual tools, and formative assessment platforms. Methodologically, I employ differentiated instruction, "
                "Bloom's Taxonomy for scaffolding concepts, and backward design to ensure lesson plans directly align with curriculum standards."
            )
        elif domain in ["software engineer", "frontend developer", "backend developer", "mobile developer", "devops engineer", "data scientist"]:
            return (
                "In my daily workflow, I rely on modern development tools including Git for version control, Docker for containerization, "
                "automated CI/CD testing pipelines, and observability dashboards. Methodologically, I follow Agile/Scrum sprints, "
                "test-driven development (TDD), and clean architecture principles to ensure code is robust, performant, and easily maintainable."
            )
        else:
            return (
                f"In my daily workflow as a {job_title}, I rely on industry-standard productivity, analytics, and collaboration tools. "
                f"Methodologically, I utilize structured workflows, continuous feedback loops, and quality checklists to ensure consistent accuracy, "
                f"accountability, and timely milestone delivery."
            )

    # 3. Challenging Problem / STAR Resolution
    if any(w in q_text for w in ["challenging problem", "star approach", "problem you faced", "obstacle", "complex issue"]):
        if domain == "education":
            return (
                "[Situation] In a previous academic term, several students struggled with core abstract concepts, resulting in low initial test scores. "
                "[Task] My goal was to diagnose individual learning gaps and raise student comprehension without falling behind the syllabus. "
                "[Action] I conducted quick diagnostic quizzes, introduced differentiated peer-learning groups, and incorporated hands-on real-world examples into every module. "
                "[Result] By the end of the term, average assessment scores improved by 28%, and all students successfully met course proficiencies."
            )
        elif domain in ["software engineer", "frontend developer", "backend developer", "mobile developer", "devops engineer", "data scientist"]:
            return (
                "[Situation] In a previous production release, our application experienced unexpected latency spikes under high peak traffic. "
                "[Task] My responsibility was to diagnose the root cause and restore sub-100ms response times. "
                "[Action] I analyzed profiling traces, identified redundant N+1 database queries, implemented distributed caching, and optimized database indexing. "
                "[Result] System latency dropped by 65%, API throughput doubled, and zero downtime incidents occurred during subsequent high-traffic events."
            )
        else:
            return (
                "[Situation] During a critical initiative, unexpected resource constraints threatened our core project deadline. "
                "[Task] My responsibility was to maintain deliverable quality while realigning project milestones. "
                "[Action] I conducted a rapid impact analysis, eliminated non-essential bottlenecks, reallocated high-priority tasks, and maintained transparent daily stakeholder communication. "
                "[Result] We successfully completed all deliverables on schedule, exceeding baseline performance metrics."
            )

    # 4. Scalability, Quality, & Maintenance
    if any(w in q_text for w in ["scalability", "quality", "maintainability", "production environments", "standards"]):
        if domain == "education":
            return (
                "I ensure educational quality and long-term consistency by maintaining detailed curriculum documentation, "
                "utilizing standardized rubrics for transparent grading, and conducting periodic student feedback loops to continuously refine teaching strategies."
            )
        elif domain in ["software engineer", "frontend developer", "backend developer", "mobile developer", "devops engineer", "data scientist"]:
            return (
                "I ensure production scalability and quality by enforcing automated unit and integration tests, practicing modular component design, "
                "implementing proactive health monitoring, and following infrastructure-as-code principles for predictable deployments."
            )
        else:
            return (
                f"I ensure quality and maintainability in my {job_title} work by establishing standardized operating procedures, "
                f"conducting thorough peer reviews, documenting key processes, and utilizing automated checks to catch discrepancies early."
            )

    # 5. Career Contribution / 1-Year Goals
    if any(w in q_text for w in ["contributing most", "next year", "growth", "where do you see yourself"]):
        return (
            f"Over the next year in this {job_title} role, my goal is to make an immediate positive impact by mastering the team's operational workflows, "
            f"consistently delivering high-quality outcomes, and collaborating with cross-functional peers to optimize processes. "
            f"Long-term, I aim to mentor emerging team members and drive forward-looking initiatives that support organizational growth."
        )

    # 6. Experience-based (STAR method)
    if q_type == "experience":
        if company and total_years > 0:
            return (
                f"During my time at {company} (as part of my {total_years}+ years of experience), "
                f"I was responsible for key deliverables in my role. [Situation & Task] Our team needed to achieve demanding "
                f"targets under tight timelines and limited resources. [Action] I applied {top_skills} "
                f"to plan the work systematically, set clear priorities, and coordinate closely with my colleagues and stakeholders. "
                f"[Result] As a result, we improved overall quality and efficiency, reduced errors, and consistently "
                f"met our major milestones on schedule."
            )
        elif total_years > 0:
            return (
                f"Over my {total_years}+ years of professional experience, I have handled a wide range of responsibilities. "
                f"[Situation & Task] In a recent role, our primary challenge was improving the way our team delivered results. "
                f"[Action] I applied {top_skills} to streamline processes, communicate clearly with stakeholders, and maintain high quality standards. "
                f"[Result] This approach led to smoother operations, measurable improvements, and positive feedback from management."
            )
        return (
            f"During my studies in {education}, I engaged in comprehensive coursework, practical training, and a capstone assignment. "
            f"[Situation & Task] Our objective was to solve a real-world problem relevant to our field from start to finish. "
            f"[Action] I took ownership of planning and execution using {top_skills}, organizing tasks, and keeping the team aligned. "
            f"[Result] We delivered our work on time, earned strong evaluations, and I gained valuable practical experience."
        )

    # 7. Project-based (STAR method)
    if q_type == "projects":
        proj_name = f"'{target_proj}'" if target_proj else "a key initiative I worked on"
        return (
            f"In {proj_name}, [Situation & Task] the goal was to deliver a practical, high-quality outcome addressing a real need. "
            f"[Action] I took ownership of the core execution using {top_skills}, breaking the work into clear phases, "
            f"coordinating with the people involved, and resolving obstacles through systematic analysis. "
            f"[Result] The initiative achieved its objectives reliably, demonstrating my ability to manage work "
            f"end-to-end from planning to successful completion."
        )

    # 8. Skill-based / Technical
    if q_type == "technical":
        return (
            f"I have extensive hands-on experience applying {primary_skill} in real-world situations. "
            f"[Situation & Task] When handling complex responsibilities, applying {primary_skill} correctly is essential for quality and accuracy. "
            f"[Action] I follow established best practices and professional standards, double-check critical steps, and document my work clearly. "
            f"[Result] This disciplined approach ensures my work with {primary_skill} is reliable, compliant, and easy for others to build upon."
        )

    # 9. Behavioral (STAR method tailored to theme)
    if q_type == "behavioral":
        if any(w in q_text for w in ["conflict", "disagree", "teammate", "difficult"]):
            return (
                "[Situation] In a previous role, a colleague and I had differing opinions on how to approach an important task. "
                "[Task] Our objective was to reach a decision quickly without compromising quality or team relationships. "
                "[Action] I arranged a focused discussion where we compared both approaches against key criteria—impact, timeline, and cost. "
                "[Result] We combined the best aspects of both ideas into a unified plan, which delivered results on time and strengthened our collaboration."
            )
        elif any(w in q_text for w in ["mistake", "fail", "error", "wrong"]):
            return (
                "[Situation] Early in an important assignment, an oversight on my part caused an error that was caught during review. "
                "[Task] I took direct accountability for correcting it and making sure it would not happen again. "
                "[Action] I promptly fixed the issue, informed the relevant people transparently, and introduced a simple checklist to verify that step every time. "
                "[Result] The correction was completed quickly, and the new checklist prevented similar errors going forward."
            )
        return (
            "[Situation] During a critical period, unexpected changes significantly compressed our deadline. "
            "[Task] I needed to ensure all essential work was completed without sacrificing quality. "
            "[Action] I prioritized the most important deliverables, broke them into manageable milestones, and kept everyone updated daily. "
            "[Result] We delivered on schedule with no major issues, proving the value of structured prioritization and clear communication."
        )

    # 10. Education
    if q_type == "education":
        return (
            f"My education in {education} gave me a comprehensive grounding in the core theory and principles of my field. "
            f"Beyond theory, I actively applied this knowledge through practical work involving {top_skills}. "
            f"This foundation equipped me with the analytical mindset and discipline required to succeed in a {job_title} role."
        )

    # 11. Job-specific
    if q_type == "job_specific":
        return (
            f"As a {job_title}, my core focus is on delivering accurate, high-quality results that meet the needs of the people I serve. "
            f"When approaching a new challenge, I start by clarifying the requirements and risks, then plan a structured approach leveraging {top_skills}. "
            f"Throughout the work, I emphasize quality checks, clear documentation, and open communication to ensure consistent, reliable outcomes."
        )

    # 12. Follow-up
    if q_type == "follow_up":
        return (
            f"To elaborate on that: when working with {primary_skill}, I pay close attention to accuracy, risk management, and trade-offs. "
            f"In practice, this means verifying my work carefully, tracking outcomes, and continuously improving based on feedback."
        )

    # 13. Closing
    if q_type == "closing":
        return (
            f"Thank you very much for this opportunity. I would love to learn more about the team's upcoming priorities, "
            f"the biggest challenges you are facing, and what success would look like for a {job_title} in the first 90 days."
        )

    # Fallback
    return (
        f"For this question, I structure my answer using the STAR method: outlining the Situation and Task, "
        f"explaining how I applied {top_skills} during the Action phase, and highlighting the measurable Result."
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
