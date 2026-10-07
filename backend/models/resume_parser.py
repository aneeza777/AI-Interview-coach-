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
# Universal Multi-Industry Skills & Keywords (100% Domain-Agnostic)
# ──────────────────────────────────────────────
UNIVERSAL_SKILLS_KEYWORDS = [
    # ── 1. Technology, Software, AI & Data ──
    "python", "java", "javascript", "typescript", "c++", "c#", "golang", "rust",
    "react", "angular", "vue", "next.js", "node.js", "express", "django", "flask",
    "fastapi", "spring boot", "html", "css", "sass", "tailwind", "bootstrap",
    "sql", "mysql", "postgresql", "mongodb", "redis", "firebase", "supabase",
    "aws", "azure", "gcp", "alibaba cloud", "docker", "kubernetes", "terraform", "ci/cd",
    "git", "github", "gitlab", "jenkins", "linux", "bash", "powershell",
    "machine learning", "deep learning", "nlp", "computer vision", "tensorflow",
    "pytorch", "scikit-learn", "pandas", "numpy", "matplotlib", "jupyter",
    "rest api", "graphql", "microservices", "agile", "scrum", "jira",
    "blockchain", "solidity", "web3", "ethereum",
    "android", "ios", "flutter", "react native", "kotlin", "swift",
    "devops", "monitoring", "logging", "grafana", "prometheus",
    "cybersecurity", "penetration testing", "network security", "cryptography",
    
    # ── 2. Healthcare, Medicine & Pharmaceuticals ──
    "clinical practice", "patient care", "diagnostics", "surgery", "pharmacology",
    "pathology", "emergency medicine", "nursing", "pediatrics", "cardiology",
    "oncology", "radiology", "internal medicine", "public health", "clinical research",
    "medical records", "ehr", "emr", "hipaa", "infection control", "phlebotomy",
    "vital signs", "triage", "medical ethics", "pharmacotherapy", "biostatistics",
    "patient assessment", "healthcare management", "telemedicine", "medical billing",
    
    # ── 3. Finance, Banking, Accounting & Audit ──
    "financial modeling", "financial analysis", "accounting", "auditing", "taxation",
    "gaap", "ifrs", "budgeting", "forecasting", "quickbooks", "sap", "tally",
    "portfolio management", "risk management", "credit analysis", "corporate finance",
    "investment banking", "equity research", "valuation", "internal audit",
    "balance sheet", "cash flow management", "p&l management", "mergers and acquisitions",
    "capital markets", "wealth management", "financial reporting", "cost accounting",
    
    # ── 4. Engineering (Mechanical, Civil, Electrical, Industrial) ──
    "autocad", "solidworks", "matlab", "thermodynamics", "fluid mechanics",
    "structural analysis", "finite element analysis", "fea", "circuit design",
    "pcb design", "plc programming", "scada", "hvac", "power systems",
    "construction management", "site supervision", "surveying", "geotechnical engineering",
    "lean manufacturing", "six sigma", "quality assurance", "quality control", "iso 9001",
    "cad/cam", "embedded systems", "robotics", "instrumentation", "safety engineering",
    
    # ── 5. Marketing, Advertising, PR & Content ──
    "digital marketing", "seo", "sem", "search engine optimization", "content strategy",
    "content marketing", "copywriting", "social media marketing", "brand management",
    "google analytics", "google ads", "meta ads", "email marketing", "market research",
    "public relations", "influencer marketing", "growth hacking", "lead generation",
    "crm", "hubspot", "mailchimp", "conversion rate optimization", "cro", "creative direction",
    
    # ── 6. Sales, Business Development & Commercial ──
    "b2b sales", "b2c sales", "account management", "business development",
    "sales strategy", "client relations", "cold calling", "sales prospecting",
    "contract negotiation", "pipeline management", "salesforce", "customer retention",
    "consultative selling", "relationship building", "revenue growth", "deal closing",
    
    # ── 7. Human Resources (HR) & Talent Acquisition ──
    "talent acquisition", "recruiting", "human resources", "hr management",
    "employee relations", "onboarding", "performance management", "labor law",
    "compensation and benefits", "hris", "workday", "bamboohr", "talent management",
    "succession planning", "conflict resolution", "employee engagement", "organizational culture",
    
    # ── 8. Legal, Compliance & Governance ──
    "legal research", "contract drafting", "contract negotiation", "litigation",
    "corporate law", "regulatory compliance", "intellectual property", "due diligence",
    "arbitration", "dispute resolution", "corporate governance", "commercial law",
    "legal writing", "case management", "risk mitigation",
    
    # ── 9. Design, Creative Arts & Architecture ──
    "graphic design", "ui/ux", "ui design", "ux design", "figma", "adobe xd",
    "photoshop", "illustrator", "indesign", "after effects", "premiere pro",
    "wireframing", "prototyping", "user research", "3d modeling", "blender",
    "typography", "video editing", "animation", "motion graphics", "architectural design",
    
    # ── 10. Education, Teaching & Academia ──
    "curriculum development", "instructional design", "classroom management",
    "lesson planning", "pedagogy", "student assessment", "e-learning", "mentorship",
    "academic research", "educational leadership", "learning management system", "canvas", "moodle",
    
    # ── 11. Supply Chain, Logistics & Operations ──
    "supply chain management", "logistics", "procurement", "inventory management",
    "vendor management", "operations management", "warehouse management", "freight forwarding",
    "distribution", "fleet management", "demand planning", "erp systems", "import export",
    
    # ── 12. Universal Soft Skills & Professional Attributes ──
    "communication", "leadership", "teamwork", "problem solving",
    "project management", "critical thinking", "time management", "decision making",
    "adaptability", "negotiation", "emotional intelligence", "public speaking",
    "presentation skills", "customer service", "stakeholder management"
]

EDUCATION_KEYWORDS = [
    # Universal Degrees across all disciplines
    "bachelor", "master", "phd", "doctorate", "diploma", "certificate", "degree",
    "university", "college", "institute", "school", "academy",
    # Tech & Science
    "bs", "ms", "bsc", "msc", "btech", "mtech", "bca", "mca",
    "computer science", "software engineering", "information technology",
    "data science", "artificial intelligence", "biotechnology",
    # Business, Commerce & Finance
    "bba", "mba", "b.com", "m.com", "finance", "accounting", "economics",
    "chartered accountant", "ca", "acca", "cfa", "cma", "banking",
    # Medical, Nursing & Pharmacy
    "mbbs", "bds", "pharmd", "pharmacy", "medicine", "nursing", "bscn", "surgery",
    "health sciences", "physiotherapy", "dpt", "veterinary",
    # Engineering
    "electrical engineering", "mechanical engineering", "civil engineering",
    "chemical engineering", "aerospace engineering", "industrial engineering", "be",
    # Law & Humanities
    "llb", "llm", "law", "arts", "ba", "ma", "psychology", "education",
    "journalism", "mass communication", "international relations", "english literature",
    "architecture", "b.arch", "m.arch", "fine arts", "graphic design",
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
# 100% Dynamic Multi-Domain Skill Extraction (AI + NLP)
# ──────────────────────────────────────────────
def _extract_skills_from_section(text: str) -> List[str]:
    """Dynamically parse skills from any resume's dedicated Skills / Competencies section."""
    lines = text.split("\n")
    in_skills_section = False
    section_skills = []

    skill_headers = [
        "skills", "technical skills", "core competencies", "key skills",
        "areas of expertise", "professional skills", "specializations",
        "tools & technologies", "competencies", "key proficiencies",
        "clinical skills", "technical proficiencies", "tools", "expertise"
    ]
    stop_headers = [
        "experience", "work experience", "employment", "professional experience",
        "education", "academic background", "projects", "certifications",
        "publications", "awards", "languages", "references", "summary",
        "profile", "about me", "interests", "hobbies"
    ]

    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
        line_lower = line_clean.lower().rstrip(":")

        # Check if line is a skills header
        if any(line_lower == h or line_lower.startswith(h + ":") or line_lower == h.upper() for h in skill_headers):
            in_skills_section = True
            # Check if header line itself has inline skills, e.g. "Skills: Python, SQL"
            if ":" in line_clean:
                remainder = line_clean.split(":", 1)[1].strip()
                if remainder:
                    for item in re.split(r'[,;•|\/]+', remainder):
                        cleaned_item = item.strip().strip("-•* ")
                        if 2 <= len(cleaned_item) <= 40 and not cleaned_item.lower().startswith(("http", "www")):
                            section_skills.append(cleaned_item.title())
            continue

        # Check if line entered a different section
        if in_skills_section:
            if any(line_lower == h or line_lower.startswith(h + ":") or line_lower == h.upper() for h in stop_headers):
                in_skills_section = False
                break

            # Parse skills line (comma, bullet, pipe, or newline delimited)
            # Remove leading bullet symbols
            cleaned_line = re.sub(r'^[•\-\*\d\.\)\s]+', '', line_clean).strip()
            # If line has category prefix like "Programming: Java, C++" or "Clinical: Triage, EHR"
            if ":" in cleaned_line and len(cleaned_line.split(":", 1)[0].split()) <= 3:
                cleaned_line = cleaned_line.split(":", 1)[1].strip()

            items = re.split(r'[,;•|\/\t]+', cleaned_line)
            for item in items:
                skill_cand = item.strip().strip("-•* ")
                # Validation: 2-35 chars, doesn't look like full sentence or contact info
                if 2 <= len(skill_cand) <= 35 and not any(ch in skill_cand for ch in ['@', 'www.', 'http', 'phone:']):
                    if len(skill_cand.split()) <= 4:
                        section_skills.append(skill_cand.title())

    return section_skills


def extract_skills(text: str) -> List[str]:
    """
    Extract technical, domain, and soft skills across ANY industry
    using dynamic section parsing + universal multi-domain dictionary + spaCy NLP.
    """
    found_skills = []
    text_lower = text.lower()

    # 1. First, extract directly from any candidate Skills/Competencies section
    section_skills = _extract_skills_from_section(text)
    found_skills.extend(section_skills)

    # 2. Match against universal multi-industry vocabulary
    for skill in UNIVERSAL_SKILLS_KEYWORDS:
        if len(skill) <= 4:
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, text_lower):
                found_skills.append(skill.title())
        else:
            if skill in text_lower:
                found_skills.append(skill.title())

    # 3. Use spaCy NER and noun-chunks for domain-specific terminology discovery
    if nlp and len(found_skills) < 15:
        doc = nlp(text[:4000])
        for chunk in doc.noun_chunks:
            chunk_text = chunk.text.strip().lower()
            # Keep clean 2-3 word technical/professional phrases
            if 4 <= len(chunk_text) <= 30 and len(chunk_text.split()) in [1, 2, 3]:
                if any(w in UNIVERSAL_SKILLS_KEYWORDS for w in chunk_text.split()):
                    found_skills.append(chunk.text.strip().title())

    # Deduplicate while preserving order
    return list(dict.fromkeys(found_skills))


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
    """Extract education-related lines from resume, strictly rejecting contact numbers and emails."""
    education_lines = []
    section_lines = []
    lines = text.split("\n")

    edu_headers = ("education", "academic background", "qualifications", "academics",
                   "academic qualifications", "educational background", "education & training")
    stop_headers = ("experience", "work experience", "employment", "professional experience",
                    "skills", "key skills", "core competencies", "projects", "certifications",
                    "publications", "awards", "languages", "references", "summary", "profile",
                    "interests", "hobbies", "achievements")
    in_edu = False

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        line_lower = line_stripped.lower()
        header_key = line_lower.rstrip(":").strip()

        # Track Education section boundaries
        if header_key in edu_headers:
            in_edu = True
            continue
        if in_edu and (header_key in stop_headers or any(header_key.startswith(h + ":") for h in stop_headers)):
            in_edu = False

        # Reject pure contact lines
        if any(c in line_lower for c in ['@', 'email', 'cell:', 'phone:', 'tel:', 'contact:', 'github.com', 'linkedin.com']):
            # If line has degree keywords, clean the contact prefix out
            line_stripped = re.sub(r'(?:cell|phone|tel|contact|mobile)\s*:\s*[\+\d\s\-\.\(\)]+', '', line_stripped, flags=re.IGNORECASE)
            line_stripped = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '', line_stripped)
            line_stripped = re.sub(r'\+?\d[\d\s\-\.\(\)]{7,}\d', '', line_stripped).strip()
            line_lower = line_stripped.lower()

        # Clean any leftover phone numbers or extra symbols
        cleaned = re.sub(r'\+?\d[\d\s\-\.\(\)]{7,}\d', '', line_stripped).strip()
        cleaned = re.sub(r'^[•\-\*\d\.\)\s]+', '', cleaned).strip()
        if len(cleaned) <= 3:
            continue

        if in_edu:
            section_lines.append(cleaned)
            continue

        # Fallback keyword scan (whole-word only, short lines only to avoid experience bullets)
        if len(cleaned.split()) > 14:
            continue
        if any(re.search(rf"(?<![a-z]){re.escape(kw)}(?![a-z])", line_lower) for kw in EDUCATION_KEYWORDS) \
                or re.search(r"\b(b|m)\.?\s?(sc|ed|com|a|s|e|phil|arch)\b\.?", line_lower) \
                or re.search(r"\bll\.?\s?[bm]\b", line_lower):
            if ":" in cleaned and cleaned.split(":", 1)[0].strip().lower() in ("skills", "key skills", "core competencies"):
                continue
            education_lines.append(cleaned)

    return (section_lines or education_lines)[:5]


# ──────────────────────────────────────────────
# Project extraction
# ──────────────────────────────────────────────
def extract_projects(text: str) -> List[str]:
    """Extract project titles or significant project descriptions from resume."""
    project_lines = []
    lines = text.split("\n")
    in_project_section = False
    
    project_headers = ["projects", "personal projects", "academic projects", "key projects", "notable projects"]
    stop_headers = ["skills", "technical skills", "education", "experience", "work experience", "certifications", "interests", "awards", "references"]

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        line_lower = line_stripped.lower()

        # Check section header
        if any(line_lower == h or line_lower.startswith(h + ":") or line_lower == h.upper() for h in project_headers):
            in_project_section = True
            continue
        elif in_project_section and any(line_lower == h or line_lower.startswith(h + ":") or line_lower == h.upper() for h in stop_headers):
            in_project_section = False

        if in_project_section:
            # Bullet point or project title line
            cleaned = re.sub(r'^[•\-\*\d\.\)\s]+', '', line_stripped).strip()
            if len(cleaned) > 4 and not cleaned.lower().startswith(("github.com", "http", "www")):
                # Filter out pure tech stack lists (e.g. "Tech: React, Node")
                if not cleaned.lower().startswith(("technologies:", "tech stack:", "tools:")):
                    project_lines.append(cleaned)
        else:
            # Look for explicit project indicators in single lines
            if any(term in line_lower for term in ["developed an app", "built a platform", "created a system", "designed a portal", "full stack project", "machine learning project"]):
                cleaned = re.sub(r'^[•\-\*\d\.\)\s]+', '', line_stripped).strip()
                if cleaned:
                    project_lines.append(cleaned)

    return project_lines[:5]


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
# Automatic target-role / field inference (any industry)
# ──────────────────────────────────────────────
# Generic role nouns used only to spot a CV headline like "Civil Engineer" or
# "Registered Nurse" near the top of the document.
_ROLE_NOUNS = (
    "engineer", "developer", "doctor", "physician", "surgeon", "nurse", "pharmacist",
    "dentist", "accountant", "auditor", "analyst", "banker", "consultant", "manager",
    "teacher", "lecturer", "professor", "lawyer", "advocate", "attorney", "designer",
    "architect", "scientist", "officer", "executive", "specialist", "technician",
    "therapist", "marketer", "recruiter", "administrator", "coordinator", "director",
    "researcher", "writer", "editor", "assistant", "associate", "intern", "trainer",
)

# Domain evidence vocab (scored by frequency across the whole CV).
_DOMAIN_EVIDENCE = {
    "Healthcare Professional": ["patient", "clinical", "hospital", "mbbs", "nursing", "diagnosis", "medical", "ward", "pharmacy", "surgery", "triage", "ehr"],
    "Finance & Accounting Professional": ["financial", "accounting", "audit", "ifrs", "gaap", "tax", "ledger", "reconciliation", "acca", "budget", "banking", "invoice"],
    "Civil Engineer": ["civil", "structural", "autocad", "construction", "site", "concrete", "surveying", "boq", "etabs"],
    "Mechanical Engineer": ["mechanical", "solidworks", "thermodynamics", "hvac", "manufacturing", "cad", "fea", "machining"],
    "Electrical Engineer": ["electrical", "circuit", "plc", "power systems", "scada", "voltage", "electronics", "wiring"],
    "Marketing Professional": ["marketing", "seo", "campaign", "brand", "social media", "content", "advertising", "google ads"],
    "Sales Professional": ["sales", "revenue", "quota", "client acquisition", "crm", "pipeline", "lead generation"],
    "HR Professional": ["recruitment", "human resources", "payroll", "onboarding", "talent", "employee relations"],
    "Legal Professional": ["legal", "litigation", "contract", "court", "llb", "compliance", "drafting", "counsel"],
    "Teacher / Educator": ["teaching", "students", "curriculum", "lesson", "classroom", "pedagogy", "lecturer"],
    "Supply Chain Professional": ["supply chain", "logistics", "procurement", "inventory", "warehouse", "vendor"],
    "Graphic Designer": ["photoshop", "illustrator", "figma", "branding", "typography", "graphic"],
    "Software Developer": ["python", "javascript", "react", "api", "git", "database", "backend", "frontend", "software"],
    "Data Scientist": ["machine learning", "data analysis", "pandas", "tensorflow", "statistics", "model"],
}


def infer_target_role(text: str) -> str:
    """
    Infer the candidate's field / target role directly from their CV.
    1) Look for a short headline near the top (e.g. "Registered Nurse", "Civil Engineer").
    2) Otherwise, score every domain by keyword frequency across the full text.
    Returns a human-readable role label; "General Professional" if nothing is found.
    """
    if not text:
        return "General Professional"

    # 1. Headline detection in the first few lines
    for line in [l.strip() for l in text.split("\n")[:8] if l.strip()]:
        low = line.lower()
        if any(ch in low for ch in ["@", "http", "www", "+92", "phone", "cell"]):
            continue
        words = re.findall(r"[a-zA-Z&/]+", line)
        if 1 <= len(words) <= 6 and any(re.search(rf"\b{n}s?\b", low) for n in _ROLE_NOUNS):
            # Strip separators like "|" and keep the role chunk that holds the noun
            for chunk in re.split(r"[|•,–\-]", line):
                c = chunk.strip()
                if c and any(re.search(rf"\b{n}s?\b", c.lower()) for n in _ROLE_NOUNS):
                    return c.title()[:60]

    # 2. Frequency-based domain scoring
    low_text = text.lower()
    scores = {}
    for role, vocab in _DOMAIN_EVIDENCE.items():
        scores[role] = sum(len(re.findall(rf"\b{re.escape(v)}\b", low_text)) for v in vocab)
    best_role, best_score = max(scores.items(), key=lambda kv: kv[1])
    return best_role if best_score >= 3 else "General Professional"


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
            "inferred_role": str,
        }
    """
    raw_text = extract_text_from_pdf(pdf_path)
    return parse_resume_text(raw_text)


def parse_resume_text(raw_text: str) -> Dict:
    """Parse already-extracted resume text (any field / industry)."""
    skills = extract_skills(raw_text)
    experience = extract_experience(raw_text)
    education = extract_education(raw_text)

    # Remove spaCy ORG false positives (skills, degrees, role titles mistaken for companies)
    skill_set = {s.lower() for s in skills}
    edu_blob = " ".join(education).lower()
    clean_companies = []
    for c in experience.get("companies", []):
        cl = c.lower().strip()
        if "\n" in c or len(cl) <= 3:
            continue
        parts = [p.strip() for p in cl.split(",") if p.strip()]
        if cl in skill_set or any(p in skill_set for p in parts) or (len(cl) <= 6 and cl in edu_blob):
            continue
        if any(re.search(rf"\b{n}s?\b", cl) for n in _ROLE_NOUNS):
            continue
        clean_companies.append(c)
    experience["companies"] = clean_companies

    return {
        "name": extract_name(raw_text),
        "raw_text": raw_text,
        "skills": skills,
        "experience": experience,
        "education": education,
        "projects": extract_projects(raw_text),
        "inferred_role": infer_target_role(raw_text),
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
