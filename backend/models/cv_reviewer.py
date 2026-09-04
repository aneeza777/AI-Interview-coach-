"""
CV Reviewer Module
==================
Analyzes a resume/CV like a real recruiter and highlights issues:
1. Missing critical sections (contact, summary, experience, education, skills)
2. Formatting and ATS issues
3. Weak language / missing action verbs
4. Missing quantifiable achievements/metrics
5. Too short / too long
6. Keyword density / stuffing detection
7. Grammar/spelling red flags
8. Suggestions for improvement
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple
from models.resume_parser import extract_text_from_pdf


# ──────────────────────────────────────────────
# Critical sections recruiters expect
# ──────────────────────────────────────────────
SECTION_KEYWORDS = {
    "contact": ["email", "phone", "mobile", "linkedin", "github", "address", "@", "+92"],
    "summary": ["summary", "objective", "profile", "about me", "career objective"],
    "experience": ["experience", "work experience", "employment", "internship", "professional experience"],
    "education": ["education", "degree", "university", "college", "institute", "bachelor", "master"],
    "skills": ["skills", "technical skills", "competencies", "technologies"],
    "projects": ["projects", "personal projects", "academic projects"],
    "certifications": ["certifications", "certificates", "awards"],
}

# Action verbs recruiters love
ACTION_VERBS = [
    "led", "managed", "developed", "built", "designed", "implemented", "deployed",
    "optimized", "improved", "increased", "decreased", "reduced", "created", "launched",
    "architected", "engineered", "automated", "streamlined", "mentored", "collaborated",
    "resolved", "achieved", "delivered", "conducted", "analyzed", "researched", "tested",
    "maintained", "refactored", "integrated", "monitored", "secured", "scaled", "migrated",
]

# Weak words to avoid
WEAK_WORDS = [
    "responsible for", "duties included", "helped with", "assisted in", "worked on",
    "participated in", "involved in", "tried to", "attempted to", "some", "various",
    "etc.", "things", "stuff", "many", "lots of", "good", "bad", "nice", "really",
]

# Common spelling red flags in Pakistani resumes
COMMON_MISSPELLINGS = {
    "recieve": "receive",
    "occured": "occurred",
    "seperate": "separate",
    "definately": "definitely",
    "accomodate": "accommodate",
    "refered": "referred",
    "successfull": "successful",
    "experiance": "experience",
    "enviroment": "environment",
    "maintainance": "maintenance",
    "comming": "coming",
    "untill": "until",
    "acurate": "accurate",
    "efficiant": "efficient",
    "oppurtunity": "opportunity",
    "prefered": "preferred",
    "developping": "developing",
    "knowlege": "knowledge",
    "persue": "pursue",
    "acheive": "achieve",
}


# ──────────────────────────────────────────────
# Section detection
# ──────────────────────────────────────────────
def detect_sections(text: str) -> Dict[str, bool]:
    """Detect which standard resume sections are present."""
    text_lower = text.lower()
    sections = {}

    for section, keywords in SECTION_KEYWORDS.items():
        sections[section] = any(kw in text_lower for kw in keywords)

    return sections


# ──────────────────────────────────────────────
# Contact info validation
# ──────────────────────────────────────────────
def check_contact_info(text: str) -> List[Dict]:
    """Check for contact information issues."""
    issues = []
    text_lower = text.lower()

    # Email check
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    if not emails:
        issues.append({
            "type": "missing",
            "severity": "high",
            "section": "contact",
            "message": "No email address found. Recruiters need this to contact you.",
            "suggestion": "Add a professional email address at the top of your CV.",
        })

    # Phone check
    phone_patterns = [
        r'(?:\+92|0)\s?3\d{2}[\s\-]?\d{7}',
        r'(?:\+92|0)\s?\d{2}[\s\-]?\d{7}',
    ]
    has_phone = any(re.search(pattern, text) for pattern in phone_patterns)
    if not has_phone:
        issues.append({
            "type": "missing",
            "severity": "high",
            "section": "contact",
            "message": "No phone number found.",
            "suggestion": "Add a Pakistani mobile number (e.g., +92 3XX XXXXXXX).",
        })

    # LinkedIn
    if "linkedin" not in text_lower:
        issues.append({
            "type": "missing",
            "severity": "medium",
            "section": "contact",
            "message": "LinkedIn profile not included.",
            "suggestion": "Add your LinkedIn URL — 95% of recruiters check it.",
        })

    # Location
    if not any(city in text_lower for city in ["karachi", "lahore", "islamabad", "rawalpindi", "faisalabad", "multan"]):
        issues.append({
            "type": "missing",
            "severity": "low",
            "section": "contact",
            "message": "City/location not clearly mentioned.",
            "suggestion": "Add your city to help recruiters assess relocation/remote fit.",
        })

    return issues


# ──────────────────────────────────────────────
# Length analysis
# ──────────────────────────────────────────────
def check_length(text: str) -> List[Dict]:
    """Check if resume length is appropriate."""
    issues = []
    words = text.split()
    word_count = len(words)

    if word_count < 150:
        issues.append({
            "type": "length",
            "severity": "high",
            "section": "overall",
            "message": f"CV is too short ({word_count} words). Looks incomplete.",
            "suggestion": "Expand to at least 300 words with experience, projects, and skills.",
        })
    elif word_count < 250:
        issues.append({
            "type": "length",
            "severity": "medium",
            "section": "overall",
            "message": f"CV is somewhat brief ({word_count} words).",
            "suggestion": "Add more detail about your achievements and projects.",
        })
    elif word_count > 900:
        issues.append({
            "type": "length",
            "severity": "medium",
            "section": "overall",
            "message": f"CV is quite long ({word_count} words). Recruiters spend ~7 seconds on first scan.",
            "suggestion": "Trim to 1-2 pages. Focus on the most relevant experience.",
        })

    return issues


# ──────────────────────────────────────────────
# Action verb & weak language analysis
# ──────────────────────────────────────────────
def check_action_verbs(text: str) -> List[Dict]:
    """Check usage of strong action verbs and weak phrases."""
    issues = []
    text_lower = text.lower()

    # Count action verbs
    action_count = sum(text_lower.count(f" {verb} ") for verb in ACTION_VERBS)

    # Count weak phrases
    weak_found = []
    for weak in WEAK_WORDS:
        if f" {weak} " in text_lower or text_lower.startswith(weak):
            weak_found.append(weak)

    if action_count < 5:
        issues.append({
            "type": "language",
            "severity": "medium",
            "section": "experience",
            "message": f"Only {action_count} strong action verbs found.",
            "suggestion": "Use verbs like 'Built', 'Led', 'Developed', 'Improved', 'Optimized' to start bullet points.",
        })

    if weak_found:
        issues.append({
            "type": "language",
            "severity": "medium",
            "section": "experience",
            "message": f"Weak phrases found: {', '.join(weak_found[:5])}",
            "suggestion": "Replace passive/weak language with strong, achievement-focused statements.",
        })

    return issues


# ──────────────────────────────────────────────
# Metrics / achievements detection
# ──────────────────────────────────────────────
def check_metrics(text: str) -> List[Dict]:
    """Check if resume includes quantifiable achievements."""
    issues = []

    # Look for numbers followed by %, x, times, etc.
    metric_patterns = [
        r'\d+\s*%',
        r'\d+x',
        r'\d+\s*(?:times|fold)',
        r'\$\d+',
        r'\d+\s*(?:users|customers|clients|requests|seconds|minutes|hours|days)',
        r'(?:increased|decreased|improved|reduced|boosted|saved|grew)\s+(?:by\s+)?\d+',
    ]

    total_metrics = 0
    for pattern in metric_patterns:
        total_metrics += len(re.findall(pattern, text, re.IGNORECASE))

    if total_metrics < 2:
        issues.append({
            "type": "achievements",
            "severity": "high",
            "section": "experience",
            "message": "No quantifiable achievements found (no %, numbers, or impact metrics).",
            "suggestion": "Add metrics like 'Improved load time by 40%', 'Built app for 5,000+ users', or 'Reduced costs by 30%'.",
        })
    elif total_metrics < 4:
        issues.append({
            "type": "achievements",
            "severity": "medium",
            "section": "experience",
            "message": f"Only {total_metrics} metrics found. Could be stronger.",
            "suggestion": "Add more numbers to show the impact of your work.",
        })

    return issues


# ──────────────────────────────────────────────
# Spelling / common errors
# ──────────────────────────────────────────────
def check_spelling(text: str) -> List[Dict]:
    """Check for common spelling mistakes in resumes."""
    issues = []
    text_lower = text.lower()

    found_errors = []
    for wrong, correct in COMMON_MISSPELLINGS.items():
        if wrong in text_lower:
            found_errors.append(f"'{wrong}' → '{correct}'")

    if found_errors:
        issues.append({
            "type": "spelling",
            "severity": "high",
            "section": "overall",
            "message": f"Spelling errors found: {', '.join(found_errors[:5])}",
            "suggestion": "Proofread your CV carefully. Spelling mistakes are the #1 reason recruiters reject resumes.",
        })

    return issues


# ──────────────────────────────────────────────
# ATS / Formatting checks
# ──────────────────────────────────────────────
def check_ats_friendly(text: str) -> List[Dict]:
    """Check if resume is ATS (Applicant Tracking System) friendly."""
    issues = []

    # Check for tables/columns indicators
    # Simple heuristic: lots of single-line short sections may indicate columns
    lines = text.split("\n")
    very_short_lines = [l for l in lines if 1 < len(l.strip()) < 20]

    if len(very_short_lines) > len(lines) * 0.4:
        issues.append({
            "type": "formatting",
            "severity": "medium",
            "section": "overall",
            "message": "Many short text fragments detected. May indicate multi-column layouts or tables.",
            "suggestion": "Use a single-column layout for better ATS parsing.",
        })

    # Check for special characters that may confuse ATS
    special_chars = len(re.findall(r'[^\w\s\-\.\,\(\)\/\@\:\;\%\+]', text))
    if special_chars > 20:
        issues.append({
            "type": "formatting",
            "severity": "low",
            "section": "overall",
            "message": f"Many special characters found ({special_chars}). Some ATS systems may struggle.",
            "suggestion": "Keep formatting simple — avoid icons, symbols, and unusual characters.",
        })

    return issues


# ──────────────────────────────────────────────
# Keyword density check
# ──────────────────────────────────────────────
def check_keyword_density(text: str) -> List[Dict]:
    """Detect keyword stuffing."""
    issues = []
    text_lower = text.lower()
    words = re.findall(r'\b\w+\b', text_lower)

    from collections import Counter
    word_freq = Counter(words)

    # Find words repeated unusually often
    total_words = len(words)
    if total_words == 0:
        return issues

    stuffing = []
    for word, count in word_freq.most_common(10):
        if len(word) > 3:
            density = count / total_words
            if density > 0.05:  # More than 5% of all words
                stuffing.append((word, round(density * 100, 1)))

    if stuffing:
        examples = ", ".join([f"'{w}' ({p}%)" for w, p in stuffing[:3]])
        issues.append({
            "type": "keyword_stuffing",
            "severity": "medium",
            "section": "skills",
            "message": f"Possible keyword stuffing: {examples}",
            "suggestion": "Use keywords naturally. ATS flags resumes with unnatural repetition.",
        })

    return issues


# ──────────────────────────────────────────────
# Overall CV review
# ──────────────────────────────────────────────
def review_cv(pdf_path: str) -> Dict:
    """
    Complete CV review pipeline.

    Returns:
        {
            "score": int (0-100),
            "grade": str (A/B/C/D/F),
            "sections_found": Dict[str, bool],
            "issues": List[Dict],
            "strengths": List[str],
            "improvement_plan": List[str],
            "summary": str,
        }
    """
    text = extract_text_from_pdf(pdf_path)

    sections = detect_sections(text)
    all_issues = []

    # Run all checks
    all_issues.extend(check_contact_info(text))
    all_issues.extend(check_length(text))
    all_issues.extend(check_action_verbs(text))
    all_issues.extend(check_metrics(text))
    all_issues.extend(check_spelling(text))
    all_issues.extend(check_ats_friendly(text))
    all_issues.extend(check_keyword_density(text))

    # Section issues
    section_issues = []
    required_sections = ["contact", "summary", "experience", "education", "skills"]
    for section in required_sections:
        if not sections.get(section):
            section_issues.append({
                "type": "missing_section",
                "severity": "high" if section in ["contact", "experience", "skills"] else "medium",
                "section": section,
                "message": f"'{section.title()}' section not clearly found.",
                "suggestion": f"Add a clear '{section.title()}' heading to your CV.",
            })

    all_issues = section_issues + all_issues

    # ── Calculate score ──
    base_score = 100
    severity_penalty = {"high": 15, "medium": 8, "low": 3}

    for issue in all_issues:
        base_score -= severity_penalty.get(issue["severity"], 5)

    # Bonus for extra sections
    bonus_sections = ["projects", "certifications"]
    for section in bonus_sections:
        if sections.get(section):
            base_score += 3

    score = max(0, min(100, base_score))

    # ── Grade ──
    if score >= 85:
        grade = "A"
        grade_label = "Excellent"
    elif score >= 70:
        grade = "B"
        grade_label = "Good"
    elif score >= 55:
        grade = "C"
        grade_label = "Fair"
    elif score >= 40:
        grade = "D"
        grade_label = "Needs Work"
    else:
        grade = "F"
        grade_label = "Major Issues"

    # ── Identify strengths ──
    strengths = []
    if sections.get("experience") and sections.get("skills") and sections.get("education"):
        strengths.append("All core sections (Experience, Education, Skills) are present.")
    if len([i for i in all_issues if i["type"] == "achievements"]) == 0:
        strengths.append("Good use of quantifiable achievements/metrics.")
    if len([i for i in all_issues if i["type"] == "language"]) == 0:
        strengths.append("Strong action verbs and professional language.")
    if sections.get("projects"):
        strengths.append("Projects section included — great for fresh graduates.")
    if sections.get("certifications"):
        strengths.append("Certifications listed — adds credibility.")
    if not strengths:
        strengths.append("Resume uploaded successfully. Address the issues below to improve.")

    # ── Improvement plan (top priorities) ──
    high_priority = [i for i in all_issues if i["severity"] == "high"]
    medium_priority = [i for i in all_issues if i["severity"] == "medium"]

    improvement_plan = []
    for issue in high_priority[:3]:
        improvement_plan.append(issue["suggestion"])
    for issue in medium_priority[:2]:
        improvement_plan.append(issue["suggestion"])

    if not improvement_plan:
        improvement_plan.append("Your CV looks great! Keep it updated with latest projects.")

    # ── Summary ──
    summary = (
        f"CV Score: {score}/100 (Grade {grade} — {grade_label}). "
        f"Found {len(high_priority)} high, {len(medium_priority)} medium, and "
        f"{len([i for i in all_issues if i['severity'] == 'low'])} low priority issues."
    )

    return {
        "score": score,
        "grade": grade,
        "grade_label": grade_label,
        "sections_found": sections,
        "issues": all_issues,
        "strengths": strengths,
        "improvement_plan": improvement_plan,
        "summary": summary,
        "word_count": len(text.split()),
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python cv_reviewer.py <path_to_resume.pdf>")
    else:
        result = review_cv(sys.argv[1])
        print(f"Score: {result['score']}/100 ({result['grade']})")
        print(f"Summary: {result['summary']}")
        print(f"\nIssues:")
        for issue in result["issues"]:
            print(f"  [{issue['severity'].upper()}] {issue['message']}")
