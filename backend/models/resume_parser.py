"""
Resume Parser Module
====================
Extracts skills, experience, education, and personal info from PDF resumes
using pdfplumber (text extraction) + spaCy (NER + keyword extraction).
"""

import re
import spacy
import pdfplumber
from pathlib import Path
from typing import Dict, List, Optional


# Load spaCy model (download once: python -m spacy download en_core_web_sm)
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("[WARNING] spaCy model 'en_core_web_sm' not found.")
    print("Run: python -m spacy download en_core_web_sm")
    nlp = None


# ──────────────────────────────────────────────
# Common skill keywords for matching
# ──────────────────────────────────────────────
TECH_SKILLS_KEYWORDS = [
    "python", "java", "javascript", "typescript", "c++", "c#", "golang", "rust",
    "react", "angular", "vue", "next.js", "node.js", "express", "django", "flask",
    "fastapi", "spring boot", "html", "css", "sass", "tailwind", "bootstrap",
    "sql", "mysql", "postgresql", "mongodb", "redis", "firebase", "supabase",
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ci/cd",
    "git", "github", "gitlab", "jenkins", "linux", "bash", "powershell",
    "machine learning", "deep learning", "nlp", "computer vision", "tensorflow",
    "pytorch", "scikit-learn", "pandas", "numpy", "matplotlib", "jupyter",
    "rest api", "graphql", "microservices", "agile", "scrum", "jira",
    "figma", "photoshop", "illustrator", "ui/ux", "wireframing",
    "data analysis", "data science", "power bi", "tableau", "excel",
    "communication", "leadership", "teamwork", "problem solving",
    "project management", "critical thinking", "time management",
    "html5", "css3", "es6", "oop", "design patterns", "testing",
    "unit testing", "jest", "mocha", "selenium", "cypress",
    "blockchain", "solidity", "web3", "ethereum",
    "android", "ios", "flutter", "react native", "kotlin", "swift",
    "devops", "monitoring", "logging", "grafana", "prometheus",
    "oauth", "jwt", "authentication", "authorization", "security",
    "webpack", "vite", "babel", "eslint", "prettier",
]

EDUCATION_KEYWORDS = [
    "bachelor", "master", "phd", "diploma", "certificate", "degree",
    "university", "college", "institute", "school", "academy",
    "bs", "ms", "mba", "btech", "mtech", "bca", "mca", "bba",
    "computer science", "software engineering", "information technology",
    "data science", "artificial intelligence", "electrical engineering",
]

EXPERIENCE_INDICATORS = [
    "experience", "worked", "developed", "managed", "led", "built",
    "designed", "implemented", "deployed", "maintained", "optimized",
    "intern", "internship", "freelance", "contract", "full-time",
    "senior", "junior", "lead", "manager", "engineer", "developer",
    "analyst", "consultant", "architect", "director", "vp",
    "year", "years", "month", "months",
]

# Words that indicate an ORG entity is actually a job title / education /
# resume section rather than a real company name.
NON_COMPANY_WORDS = {
    # job titles / roles
    "engineer", "developer", "programmer", "manager", "analyst", "consultant",
    "architect", "designer", "intern", "lead", "director", "officer",
    "specialist", "associate", "coordinator", "founder", "head", "ceo",
    "cto", "cfo", "president", "vice", "senior", "junior", "chief",
    "software", "data", "web", "mobile", "front", "back", "full",
    "freelance", "self", "employed", "remote", "contract",
    # education
    "university", "college", "institute", "school", "academy", "education",
    "degree", "bachelor", "master", "phd", "diploma", "bs", "ms", "mba",
    "btech", "mtech", "science", "engineering", "technology", "arts",
    "department", "faculty", "campus", "student",
    # resume section headers / generic
    "experience", "skills", "projects", "summary", "profile", "objective",
    "certifications", "achievements", "languages", "interests", "references",
}


# ──────────────────────────────────────────────
# Text extraction from PDF
# ──────────────────────────────────────────────
def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract raw text from a PDF file using pdfplumber."""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        raise ValueError(f"Failed to read PDF: {e}")

    if not text.strip():
        raise ValueError("Could not extract any text from the PDF. Is it image-based?")

    return text.strip()


# ──────────────────────────────────────────────
# Skill extraction
# ──────────────────────────────────────────────
def extract_skills(text: str) -> List[str]:
    """Extract technical/soft skills by keyword matching."""
    text_lower = text.lower()
    found_skills = []

    for skill in TECH_SKILLS_KEYWORDS:
        # Use word boundary matching for short skills
        if len(skill) <= 4:
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, text_lower):
                found_skills.append(skill.title())
        else:
            if skill in text_lower:
                found_skills.append(skill.title())

    return list(dict.fromkeys(found_skills))  # deduplicate, preserve order


# ──────────────────────────────────────────────
# Experience extraction
# ──────────────────────────────────────────────
def extract_experience(text: str) -> Dict:
    """Extract experience details using keyword matching and NER."""
    lines = text.split("\n")
    experience_lines = []
    job_titles = []
    companies = []
    total_years = 0

    # Try to find total years of experience
    years_pattern = r'(\d+)\+?\s*(?:years?|yrs?\.?)\s*(?:of)?\s*(?:experience|exp\.?)'
    match = re.search(years_pattern, text.lower())
    if match:
        total_years = int(match.group(1))

    # Extract job-title-like lines (lines with experience indicators)
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        line_lower = line_stripped.lower()

        # Check if line contains experience-related keywords
        if any(indicator in line_lower for indicator in EXPERIENCE_INDICATORS):
            experience_lines.append(line_stripped)

    # Use spaCy NER for organization names
    if nlp:
        doc = nlp(text[:5000])  # limit for performance
        for ent in doc.ents:
            if ent.label_ == "ORG":
                candidate = ent.text.strip()
                if candidate and candidate not in companies and _looks_like_company(candidate):
                    companies.append(candidate)

    return {
        "job_titles": job_titles[:5],
        "companies": companies[:5],
        "experience_lines": experience_lines[:10],
        "total_years": total_years,
    }


# ──────────────────────────────────────────────
# Company-name validation
# ──────────────────────────────────────────────
def _looks_like_company(name: str) -> bool:
    """
    spaCy's ORG tagger often labels job titles and education as organizations.
    Filter out anything that is clearly a role, education, or section header.
    """
    if not name:
        return False
    
    name_lower = name.lower().strip()
    
    # Reject if it looks like contact info (phone, email)
    if re.search(r'[\d\-\.]+\d{3,}', name_lower):  # Phone number pattern
        return False
    if '@' in name_lower or 'email' in name_lower:  # Email
        return False
    if '+92' in name_lower or '+1' in name_lower or '+91' in name_lower:  # International phone
        return False
    
    # Reject very long phrases (companies are usually short)
    words = re.findall(r"[a-z]+", name_lower)
    if len(words) > 4:
        return False
    # Reject if any word is a known non-company term
    for w in words:
        if w in NON_COMPANY_WORDS:
            return False
    # Reject pure numbers / dates
    if re.fullmatch(r"[\d\s\-]+", name):
        return False
    # Reject if mostly numbers (like "2023" or similar)
    digit_ratio = sum(1 for c in name if c.isdigit()) / len(name) if name else 0
    if digit_ratio > 0.3:
        return False
    
    return True


# ──────────────────────────────────────────────
# Education extraction
# ──────────────────────────────────────────────
def extract_education(text: str) -> List[str]:
    """Extract education-related lines from resume."""
    education_lines = []
    lines = text.split("\n")

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        line_lower = line_stripped.lower()

        if any(kw in line_lower for kw in EDUCATION_KEYWORDS):
            education_lines.append(line_stripped)

    return education_lines[:5]


# ──────────────────────────────────────────────
# Name extraction via spaCy NER
# ──────────────────────────────────────────────
def _is_valid_name(text: str) -> bool:
    """Check if text looks like a real person name (not contact info)."""
    if not text or len(text.strip()) < 2:
        return False
    
    text_lower = text.lower().strip()
    text_stripped = text.strip()
    
    # Reject URLs and web addresses
    if '://' in text_lower or 'www.' in text_lower:  # http://, https://, www.
        return False
    if 'github.com' in text_lower or 'linkedin.com' in text_lower:  # Social profiles
        return False
    if 'facebook.com' in text_lower or 'twitter.com' in text_lower:  # More social profiles
        return False
    if '.com' in text_lower or '.io' in text_lower or '.co' in text_lower:  # Domain extensions
        return False
    if re.search(r'[a-z0-9]+\.[a-z]{2,}', text_lower):  # Any domain pattern
        return False
    
    # Reject if looks like contact info
    if re.search(r'[\d\-\.]+\d{3,}', text_lower):  # Phone patterns
        return False
    if '@' in text_lower or 'email' in text_lower:  # Email
        return False
    if '+92' in text_lower or '+1' in text_lower or '+91' in text_lower:  # International phone
        return False
    if re.match(r'^contact\s*[:|\-]?\s*\d', text_lower):  # "Contact: 123" pattern
        return False
    if re.match(r'^(phone|mobile|whatsapp|tel)', text_lower):  # Phone section headers
        return False
    
    # Check if it has a reasonable name structure (at least 2 words or reasonable length)
    words = text_stripped.split()
    if len(words) == 1 and len(text_stripped) < 3:  # Too short single word
        return False
    
    # Must have at least one letter character
    if not any(c.isalpha() for c in text_stripped):
        return False
    
    # Should mostly be letters (not mostly numbers)
    letter_ratio = sum(1 for c in text_stripped if c.isalpha()) / len(text_stripped)
    if letter_ratio < 0.6:  # Less than 60% letters is suspicious
        return False
    
    # Reject if has slashes (typical in URLs or file paths)
    if '/' in text_stripped or '\\' in text_stripped:
        return False
    
    return True


def _extract_name_from_lines(lines: List[str]) -> Optional[str]:
    """Fallback: extract name from first few lines by heuristics."""
    for line in lines[:10]:  # Check first 10 lines
        line_stripped = line.strip()
        if not line_stripped:
            continue
        
        line_lower = line_stripped.lower()
        
        # Skip lines that clearly contain URLs or web identifiers
        if 'http' in line_lower or 'www.' in line_lower:
            continue
        if 'github.com' in line_lower or 'linkedin.com' in line_lower:
            continue
        if '.com' in line_lower or '.io' in line_lower:
            continue
        
        # Skip lines that look like contact info or section headers
        if any(kw in line_lower for kw in ['email', 'phone', 'contact', 'address', 'summary', 'experience', 'education', 'skills', 'projects', '@', '+92', '+1', '/']):
            if '@' in line_stripped or '+92' in line_stripped or '+1' in line_stripped or '/' in line_stripped:
                continue
        
        # Look for lines that might be a name (2+ words, proper case)
        if len(line_stripped) > 3 and len(line_stripped) < 60:
            # Check if it's mostly capitalized (like "John Doe")
            words = line_stripped.split()
            if len(words) >= 1:
                # Count how many words start with capital
                capitalized_words = sum(1 for w in words if w and w[0].isupper())
                if capitalized_words >= len(words) * 0.7:  # At least 70% capitalized
                    if _is_valid_name(line_stripped):
                        return line_stripped
    
    return None


def extract_name(text: str) -> Optional[str]:
    """
    Try to extract person name using multiple methods.
    
    1. First tries spaCy NER with validation
    2. Falls back to heuristic-based extraction from first lines
    3. Returns None if no valid name found
    """
    if not text:
        return None
    
    lines = text.split("\n")
    
    # Method 1: Try spaCy NER with validation
    if nlp:
        try:
            # Usually the name is in the first few lines
            first_lines = "\n".join(lines[:5])
            doc = nlp(first_lines)
            
            for ent in doc.ents:
                if ent.label_ == "PERSON":
                    extracted_name = ent.text.strip()
                    if _is_valid_name(extracted_name):
                        return extracted_name
        except Exception as e:
            print(f"[Warning] spaCy NER failed: {e}")
    
    # Method 2: Fallback to heuristic extraction
    fallback_name = _extract_name_from_lines(lines)
    if fallback_name:
        return fallback_name
    
    return None


# ──────────────────────────────────────────────
# Main parser function
# ──────────────────────────────────────────────
def parse_resume(pdf_path: str) -> Dict:
    """
    Full resume parsing pipeline.

    Returns:
        {
            "name": str,
            "raw_text": str,
            "skills": List[str],
            "experience": Dict,
            "education": List[str],
        }
    """
    raw_text = extract_text_from_pdf(pdf_path)

    return {
        "name": extract_name(raw_text),
        "raw_text": raw_text,
        "skills": extract_skills(raw_text),
        "experience": extract_experience(raw_text),
        "education": extract_education(raw_text),
    }


if __name__ == "__main__":
    # Quick test
    import sys
    if len(sys.argv) < 2:
        print("Usage: python resume_parser.py <path_to_resume.pdf>")
    else:
        result = parse_resume(sys.argv[1])
        print(f"Name: {result['name']}")
        print(f"Skills: {result['skills']}")
        print(f"Experience: {result['experience']}")
        print(f"Education: {result['education']}")
