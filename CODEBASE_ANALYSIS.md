# AI Interview Coach — Comprehensive Codebase Analysis

**Date**: 2026-08-31  
**Analysis Scope**: Question generation, answer evaluation, resume parsing, data flow, template handling

---

## Executive Summary

✅ **No "aneeza" references found** — the entire codebase uses generic test data  
⚠️ **Critical Issues Found**: 11 data mapping/template problems identified  
🔧 **Files Needing Fixes**: 6 core backend files require attention

---

## 1. Question Generation Flow

### 1.1 Overview
```
Resume PDF Upload
    ↓
Parse Resume (extract skills, experience, education, contact)
    ↓
Build Interview Plan (generate 12 adaptive questions)
    ├─ Introduction Question (1)
    ├─ CV Walkthrough Questions (3-4)
    │  └─ Uses: skills, companies, education, experience
    ├─ Behavioral Questions (2-3)
    ├─ Job-Specific Questions (2-3)
    └─ Closing Question (1)
    ↓
Each Question Includes:
    - question: str
    - type: 'introduction', 'experience', 'technical', 'behavioral', 'job_specific', 'closing'
    - expected_keywords: List[str]  (for answer evaluation)
    - difficulty: 'easy', 'medium', 'hard'
    - number: int (1-12)
```

### 1.2 Key Files & Functions

| File | Function | Purpose | Input | Output |
|------|----------|---------|-------|--------|
| `question_generator.py` | `generate_questions()` | Template-based Q generation | resume_dict, job_title, count | List[Dict] |
| `interview_engine.py` | `build_interview_plan()` | Builds adaptive interview | resume_data, job_title, mode | List[Dict] |
| `interview_engine.py` | `_generate_cv_questions()` | Resume-based questions | resume_data, job_title | List[Dict] |
| `interview_engine.py` | `_generate_job_questions()` | Job-specific questions | job_title | List[Dict] |
| `resume_parser.py` | `parse_resume()` | Extract resume data | pdf_file_path | parsed_data dict |

### 1.3 Resume Data Structure

```python
parsed_data = {
    "name": "John Doe",  # or None
    "skills": ["Python", "React", "Docker"],
    "experience": {
        "companies": ["TechCorp", "StartupXYZ"],
        "job_titles": [],
        "total_years": 3,
        "experience_lines": [...]
    },
    "education": ["BS Computer Science"],
    "contact": {
        "emails": ["john@example.com"],
        "phones": ["+92-300-1234567"],
        "linkedin": "linkedin.com/in/johndoe"
    }
}
```

---

## 2. Answer Evaluation Pipeline

### 2.1 Flow
```
User Voice Answer (audio)
    ↓
Transcribe Audio → transcription_text
    ↓
Evaluate Answer:
    ├─ Keyword Matching (30%):
    │  └─ Count matched keywords from expected_keywords list
    │
    ├─ Semantic Similarity (40%):
    │  └─ Encode (question + keywords, answer)
    │  └─ Compare using sentence-transformers (all-MiniLM-L6-v2)
    │
    └─ Depth/Length Analysis (30%):
       ├─ Word count analysis (30-200 words ideal)
       ├─ Sentence variety
       ├─ Filler word count
       └─ Repetition penalty
    ↓
Evaluate Confidence (audio features):
    ├─ Speaking rate (WPM)
    ├─ Pitch variation
    ├─ Pause ratio
    ├─ Volume consistency
    └─ Pause frequency
    ↓
Combine Scores:
    ├─ content_score: 0-100
    ├─ confidence_score: 0-100
    └─ combined_score: 60% content + 40% confidence
```

### 2.2 Expected Keywords Example

**Question**: "Tell me more about your time at {company}"  
**Expected Keywords**: `["responsibility", "achieve", "result", "project", "team", "contribute", company.lower()]`

**Good Answer** (Score 75/100):
- "At TechCorp, I was responsible for building the mobile app using Flutter..."
- ✅ Matches: responsibility, project, TechCorp (company)
- ✅ Good semantic similarity
- ✅ 85 words (within 30-200 range)

**Poor Answer** (Score 25/100):
- "Yeah, I worked there. It was okay."
- ❌ Matches: none/minimal
- ❌ Low semantic similarity  
- ❌ 7 words (too short)

---

## 3. Model Answer Generation

### 3.1 Purpose
Generate ideal/sample answers for interview practice mode and CV review validation.

### 3.2 Key Function
**File**: `backend/models/interview_engine.py`, lines 500-580  
**Function**: `generate_model_answer(question, resume_data, job_title)`

### 3.3 Template Examples

#### Introduction Question
```python
f"Hello, my name is {name}. I recently completed {education}. "
f"I have around {total_years} years of experience, "
f"and my core skills include {top_skills}. "
f"I am excited about this {job_title} role..."
```

#### Experience Question
```python
f"At {company}, I spent about {total_years} years working on meaningful projects. "
f"My responsibilities included developing features, debugging issues... "
f"I used {top_skills} to deliver a feature that improved the product."
```

#### Technical Question
```python
f"I have hands-on experience with {top_skills}. In my recent work, "
f"I used them to build features, fix bugs, and optimize performance."
```

#### Job-Specific Question
```python
f"As a {job_title}, I focus on writing clean, maintainable code and "
f"working closely with the team. I start by understanding requirements..."
```

### 3.4 Data Fallbacks
```python
name = resume_data.get("name") or "the candidate"
skills = resume_data.get("skills", [])
top_skills = ", ".join(skills[:3]) if skills else "relevant technical skills"
education = education_list[0] if education_list else "my degree"
total_years = experience.get("total_years", 0) or 0
company = _pick_valid_company(companies) or ""  # None if invalid
```

---

## 4. Critical Issues Found

### ⚠️ Issue #1: Hardcoded Test Data in Production Code

**Severity**: 🔴 HIGH  
**Files Affected**:
- `backend/models/interview_engine.py` (lines 587-592)
- `backend/models/question_generator.py` (lines 450-455)

**Problem**:
```python
# In __main__ block (but could run accidentally)
sample_resume = {
    "name": "Ahmed Khan",
    "skills": ["Python", "React", "Flutter", "Django", "PostgreSQL"],
    "experience": {"companies": ["TechCorp"], "total_years": 2},
    "education": ["BS Computer Science"],
}
```

**Risk**: If this test code executes in production, interview answers would be generated for "Ahmed Khan" from "TechCorp".

**Fix Required**: 
- [ ] Move test data outside main codebase
- [ ] Add guards to prevent execution
- [ ] Use fixtures/mocks for testing

---

### ⚠️ Issue #2: Hardcoded Sample CV Data

**Severity**: 🟡 MEDIUM  
**File**: `create_sample_cv.py`

**Problem**:
```python
pdf.cell(0, 10, 'John Doe', ln=True)
pdf.cell(0, 10, 'Email: john@example.com | Phone: +92-300-1234567', ln=True)
pdf.multi_cell(0, 8, 'Software Engineer at TechCorp...')
pdf.multi_cell(0, 8, 'BS Computer Science, FAST NUCES, 2021')
```

**Used For**: Testing/demo sample resume generation

**Fix**: Clearly document this is for testing only, not production

---

### ⚠️ Issue #3: Template String Direct Interpolation Without Validation

**Severity**: 🔴 HIGH  
**File**: `backend/models/interview_engine.py`, lines 180-220

**Problem**:
```python
# These directly insert parsed resume data with NO sanitization
f"Tell me more about your time at {company}."
f"I see you have {total_years}+ years of experience."
f"What excites you about this {job_title} role?"
```

**Risk**: 
- Malformed data from resume parsing produces odd questions
- Company name contains special characters → corrupted question
- Empty arrays → references to index [0] fail silently

**Example Failure**:
```
Resume parsing returns: companies = ["CEO / Founder (Self-employed)"]
Question generated: "Tell me more about your time at CEO / Founder (Self-employed)"
❌ Incorrect — this is a role, not a company
```

**Fix Required**:
- [ ] Validate data before template interpolation
- [ ] Use `_pick_valid_company()` consistently
- [ ] Add type checking and length validation

---

### ⚠️ Issue #4: Company Name Detection is Unreliable

**Severity**: 🟡 MEDIUM  
**File**: `backend/models/resume_parser.py` + `interview_engine.py`

**Problem**:
- Uses spaCy NER to detect ORG entities
- Then filters with `_NON_COMPANY_WORDS` list
- Still produces false positives/negatives

**_NON_COMPANY_WORDS Filter** (47 words):
```python
"engineer", "developer", "software", "data", "web", "mobile",
"university", "college", "degree", "bachelor", "master", "phd",
"experience", "skills", "projects", "consultant", "manager", etc.
```

**False Negatives** (Good companies rejected):
- "Google" might be accepted
- "Startup Labs" → rejected (contains "labs" potentially)
- Multi-word companies: "McKinsey & Company" → split into words, each checked

**False Positives** (Bad entries accepted):
- "Senior Developer at Startup" → "Senior Developer" might pass
- "Self Employed" → depending on parsing

**Impact**: CV questions reference wrong companies or no company

**Fix Required**:
- [ ] Improve NER filtering or use different approach
- [ ] Validate company format (minimum 2 chars, max 50)
- [ ] Add whitelist of known companies if needed

---

### ⚠️ Issue #5: CV Reviewer Has Hardcoded Geographic Assumptions

**Severity**: 🟡 MEDIUM  
**File**: `backend/models/cv_reviewer.py`, lines 60-100

**Problem**:
```python
# Hardcoded for Pakistan only
cities = ["karachi", "lahore", "islamabad", "rawalpindi", "faisalabad", "multan"]
phone_pattern = r'(?:\+92|0)\s?3\d{2}[\s\-]?\d{7}'  # Pakistani format
```

**Issues**:
- ❌ International resumes flagged as problematic
- ❌ Non-Pakistani phone numbers rejected
- ❌ No configuration option

**Example**:
- Resume with US phone: +1 (555) 123-4567
- CV Review says: "No phone number found"
- ❌ Incorrect, violates feedback

**Fix Required**:
- [ ] Make location detection configurable
- [ ] Accept multiple phone formats
- [ ] Auto-detect country from phone/email or user input

---

### ⚠️ Issue #6: Expected Answers Never Used in Evaluation

**Severity**: 🟡 MEDIUM  
**File**: `backend/models/answer_evaluator.py`

**Problem**:
- `generate_model_answer()` creates detailed ideal answers
- But evaluation logic only uses:
  - Keyword matching against `expected_keywords`
  - Semantic similarity against (question + keywords)
  - NOT against the actual model answer

**Disconnect Example**:
```python
# Model answer generated:
model_answer = "At TechCorp, I developed scalable REST APIs using FastAPI..."

# But evaluation uses:
expected_keywords = ["responsibility", "achieve", "result", "project", "team"]
semantic_reference = question + ". " + ". ".join(expected_keywords[:10])
# ≠ model_answer
```

**Impact**: Inconsistency between what's ideal and what's evaluated

**Fix Required**:
- [ ] Use model answer in semantic similarity scoring
- [ ] Extract keywords from model answer
- [ ] Or reconsider if model answers serve purpose

---

### ⚠️ Issue #7: Missing Resume Field Handling Inconsistent

**Severity**: 🟡 MEDIUM  
**File**: `backend/models/interview_engine.py`

**Problem**:
- Some fields use `.get()` with fallbacks: ✅
- Some assume field exists: ❌

**Examples**:
```python
# Good (with fallback):
name = resume_data.get("name") or "the candidate"

# Bad (assumes presence):
education = education_list[0] if education_list else "my degree"  # But education_list might be None
```

**Issue**: If `education` is `None` instead of `[]`:
```python
education_list = resume_data.get("education", [])  # ✅ returns []
education_list = resume_data.get("education")  # ❌ returns None
education = education_list[0]  # ❌ TypeError: 'NoneType' object is not subscriptable
```

**Fix Required**:
- [ ] Standardize all `.get()` calls with proper defaults
- [ ] Use consistent type checking

---

### ⚠️ Issue #8: Contact Information Not Used in Interview

**Severity**: 🟢 LOW  
**File**: All backend files

**Problem**:
- CV Reviewer validates email, phone, LinkedIn
- But this data is NOT passed to interview generation
- Not used in questions or answers

**Question**: Should personal contact be in questions?  
**Current**: No — questions focus on experience, not contact info

**Potential Enhancement**: Could ask "What's the best way to reach you?" but currently not implemented.

---

### ⚠️ Issue #9: Dataset Generation Directory is Empty at Runtime

**Severity**: 🟡 MEDIUM  
**File**: `training/prepare_datasets.py`

**Problem**:
```
training/data/  ← This directory exists but is EMPTY
```

**What Happens**:
- `train_question_generator.py` tries to load: `DATA_PATH = training/data/question_generation_dataset.json`
- File doesn't exist at first run
- Script must run `prepare_datasets.py` first
- No error handling or documentation

**Fix Required**:
- [ ] Auto-generate datasets if missing
- [ ] Document setup process
- [ ] Add validation checks

---

### ⚠️ Issue #10: Job Title Matching is Fragile

**Severity**: 🟢 LOW  
**File**: `backend/models/interview_engine.py`, lines 157-165

**Problem**:
```python
def _match_job_title(job_title: str) -> str:
    title_lower = job_title.lower()
    for key in JOB_QUESTION_TEMPLATES:
        if key == "default":
            continue
        if any(kw in title_lower for kw in key.replace("/", " ").split()):
            return key
    return "default"
```

**Issues**:
- Substring matching (e.g., "Engineer" matches "Frontend Engineer", "Backend Engineer", "Data Engineer")
- First match wins (ordering matters)
- Many job titles → "default" questions

**Example**:
- Job Title: "Senior Machine Learning Researcher"
- Matches: "machine learning engineer" template (incorrect match)
- Result: Wrong job-specific questions

**Fix Required**:
- [ ] Improve job title classification (fuzzy matching)
- [ ] Check for exact phrase matches first
- [ ] Add more job categories

---

### ⚠️ Issue #11: No Validation of Parsed Resume Fields

**Severity**: 🟡 MEDIUM  
**File**: `backend/models/resume_parser.py`

**Problem**:
```python
def extract_skills(text: str) -> List[str]:
    """No validation of extracted skills"""
    found_skills = []
    for skill in TECH_SKILLS_KEYWORDS:
        # Keyword matching — can produce false positives
        if skill in text_lower:
            found_skills.append(skill)
    return found_skills  # No deduplication, filtering, or validation
```

**Issues**:
- Case sensitivity assumptions
- No deduplication (though `dict.fromkeys()` used later)
- False positives from keyword matching
- Years of experience extraction assumes specific format

**Example**:
- Resume text: "I have **3+ years** of **Python** experience with **Django**"
- Correctly extracts: skills = ["Python", "Django"], total_years = 3 ✅
- Resume text: "I love **python** snakes and work with **django** horse ranch"
- Incorrectly extracts: skills = ["Python", "Django"], total_years = 0 ❌

---

## 5. Data Mapping Issues Summary Table

| Issue | Component | Severity | Impact | Fix Difficulty |
|-------|-----------|----------|--------|-----------------|
| Hardcoded test data | interview_engine.py | 🔴 HIGH | "Ahmed Khan" answers in prod | Easy (delete code) |
| Template interpolation | interview_engine.py | 🔴 HIGH | Corrupted questions | Medium (add validation) |
| Company name detection | resume_parser.py | 🟡 MEDIUM | Wrong CV questions | Hard (improve NER) |
| CV reviewer geo-hardcoded | cv_reviewer.py | 🟡 MEDIUM | Rejects valid intl resumes | Easy (make configurable) |
| Model answers not used | answer_evaluator.py | 🟡 MEDIUM | Inconsistent evaluation | Medium (refactor) |
| Missing field handling | interview_engine.py | 🟡 MEDIUM | Potential crashes | Easy (standardize) |
| Contact info unused | All files | 🟢 LOW | N/A — not connected | N/A |
| Empty dataset dir | prepare_datasets.py | 🟡 MEDIUM | Training setup issue | Easy (add auto-gen) |
| Job title matching | interview_engine.py | 🟢 LOW | Wrong job questions | Medium (improve matching) |
| No field validation | resume_parser.py | 🟡 MEDIUM | False positive skills | Easy (add filters) |
| Sample CV hardcoded | create_sample_cv.py | 🟡 MEDIUM | Confusing for users | Easy (document) |

---

## 6. Resume-to-Question Flow (Detailed)

```
┌─────────────────────────────────────────────────────────────────────┐
│                       USER UPLOADS RESUME (PDF)                      │
└────────────────────────────┬──────────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     backend/main.py POST /api/resumes/upload          │
│  - Save PDF to uploads/user_{id}/resume.pdf                         │
│  - Call parse_resume(pdf_path)                                       │
└────────────────────────────┬──────────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│              backend/models/resume_parser.py parse_resume()          │
│  INPUT: /path/to/resume.pdf                                         │
│  1. extract_text_from_pdf() → raw_text                              │
│  2. extract_skills(text) → skills = ["Python", "React"]             │
│  3. extract_experience(text) → {companies, total_years, ...}        │
│  4. extract_education(text) → education = ["BS CS"]                 │
│  5. extract_contact(text) → {emails, phones, linkedin}              │
│  OUTPUT: parsed_data dict                                           │
└────────────────────────────┬──────────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│           backend/models/cv_reviewer.py review_cv()                  │
│  - Check for missing sections (contact, summary, education)         │
│  - Validate phone/email/LinkedIn format                             │
│  - Check for weak language / action verbs                           │
│  - Length validation                                                │
│  - Misspelling detection                                            │
│  OUTPUT: cv_review = [issues, suggestions]                          │
└────────────────────────────┬──────────────────────────────────────────┘
                             │
                    (Parallel Processes)
                      │                 │
        ┌─────────────↓───┐        ┌───↓──────────────────┐
        │  Store in DB    │        │  Return to Frontend  │
        │  (Resume model) │        │  (CV Review Display) │
        └────────────────┘        └──────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│          backend/main.py POST /api/interviews                        │
│  INPUT: {resume_id, job_title, mode}                                │
│  - Fetch resume from DB                                             │
│  - Call build_interview_plan(resume.parsed_data, job_title, mode)   │
└────────────────────────────┬──────────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│      backend/models/interview_engine.py build_interview_plan()      │
│  INPUT: resume_data, job_title, mode                                │
│  1. INTRODUCTION:                                                   │
│     - Pick random introduction question                             │
│     - expected_keywords = ["name", "education", "skills"]           │
│                                                                     │
│  2. CV QUESTIONS (_generate_cv_questions):                          │
│     if resume_data["experience"]["total_years"] > 0:                │
│         question = f"I see you have {total_years}+ years..."        │
│         expected_keywords = ["role", "responsibility", ...]         │
│     if resume_data["experience"]["companies"]:                      │
│         company = _pick_valid_company(companies)                    │
│         question = f"Tell me about your time at {company}"          │
│         expected_keywords = [..., company.lower()]                  │
│     if resume_data["skills"]:                                       │
│         for skill in skills[:3]:                                    │
│             question = f"Tell me about {skill}..."                  │
│             expected_keywords = [skill.lower(), ...]                │
│                                                                     │
│  3. BEHAVIORAL QUESTIONS:                                           │
│     - Pick 2-3 from BEHAVIORAL_QUESTIONS list                       │
│     - Paraphrase if needed                                          │
│     - expected_keywords pre-defined                                 │
│                                                                     │
│  4. JOB-SPECIFIC QUESTIONS (_generate_job_questions):               │
│     - Match job_title against JOB_QUESTION_TEMPLATES                │
│     - Pick 2-3 questions for matched role                           │
│     - expected_keywords = ["experience", "approach", ...]           │
│                                                                     │
│  5. CLOSING:                                                        │
│     - Pick random closing question                                  │
│     - expected_keywords = ["opportunity", "growth", ...]            │
│                                                                     │
│  6. Assign question numbers                                         │
│     - q["number"] = i + 1                                           │
│                                                                     │
│  OUTPUT: questions = [                                              │
│      {question, type, expected_keywords, difficulty, number},       │
│      {question, type, expected_keywords, difficulty, number},       │
│      ...                                                            │
│  ]                                                                  │
└────────────────────────────┬──────────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│           INTERVIEW SESSION CREATED & STORED IN DB                   │
│  Interview model:                                                   │
│  - user_id, resume_id, job_title, mode                              │
│  - questions = [...]  (JSON)                                        │
│  - current_question_index = 0                                       │
│  - status = "in_progress"                                           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 7. Question-Answer-Evaluation Flow

```
┌──────────────────────────────────────────────┐
│  USER ANSWERS QUESTION (Voice Audio)         │
│  Audio file → /uploads/user_{id}/...         │
└────────────┬─────────────────────────────────┘
             │
             ↓
┌──────────────────────────────────────────────┐
│  backend/main.py POST /api/interviews/{id}/answer
│  INPUT: {interview_id, question_number, audio}
└────────────┬─────────────────────────────────┘
             │
             ↓
┌──────────────────────────────────────────────┐
│  speech_to_text.py transcribe_audio()        │
│  INPUT: audio_file_path                      │
│  - Use Whisper or similar                    │
│  OUTPUT: {text, duration, confidence}        │
└────────────┬─────────────────────────────────┘
             │
             ↓
┌──────────────────────────────────────────────┐
│  answer_evaluator.py evaluate_answer()       │
│  INPUT: answer_text, question, expected_kw  │
│                                              │
│  1. KEYWORD MATCHING:                        │
│     score_kw = (matched_kws / total_kws)     │
│     Checks: word boundaries for short kws    │
│                                              │
│  2. SEMANTIC SIMILARITY:                     │
│     model = SentenceTransformer(...)         │
│     reference = question + kws_summary       │
│     embeddings = model.encode([answer, ref]) │
│     similarity = cosine_similarity           │
│     score_sem = normalize(similarity, -0.05, 0.55)
│                                              │
│  3. DEPTH/LENGTH ANALYSIS:                   │
│     word_count analysis (optimal: 30-200)    │
│     sentence_count analysis                  │
│     filler_word_count detection              │
│     repetition_penalty calculation           │
│     score_depth = 0.7 * length + 0.3 * variety
│                                              │
│  OUTPUT: content_eval = {                    │
│      content_score: 0-100,                   │
│      keyword_score, semantic_score, etc.     │
│      matched_keywords: [...]                 │
│      depth_analysis: {...}                   │
│      feedback: "Your answer...",             │
│      tips: ["💡 Add specific example", ...]  │
│  }                                           │
└────────────┬─────────────────────────────────┘
             │
             ↓
┌──────────────────────────────────────────────┐
│  confidence_detector.py detect_confidence()  │
│  INPUT: audio_file_path                      │
│                                              │
│  Extract features:                           │
│  - Speaking rate (WPM)                       │
│  - Pitch variation (coefficient of variation)│
│  - Pause ratio (silence / total_time)        │
│  - Volume consistency                        │
│  - Pause frequency (pauses_per_minute)       │
│                                              │
│  Score mapping:                              │
│  - Confident: 120-160 WPM, high pitch_cv     │
│  - Nervous: <100 WPM, low pitch_cv           │
│                                              │
│  OUTPUT: confidence = {                      │
│      confidence_score: 0-100,                │
│      breaking_rate, pitch_cv, etc.           │
│      feedback: "Volume inconsistent...",     │
│      tips: ["Slow down", "Project voice"]    │
│  }                                           │
└────────────┬─────────────────────────────────┘
             │
             ↓
┌──────────────────────────────────────────────┐
│  report_generator.py compile_question_result()
│  INPUT: question, transcription,             │
│         content_eval, confidence             │
│                                              │
│  Combine scores:                             │
│  combined = 0.6 * content_score +            │
│             0.4 * confidence_score           │
│                                              │
│  OUTPUT: result = {                          │
│      question_number, question, type,        │
│      transcription_text,                     │
│      content_score, confidence_score,        │
│      combined_score,                         │
│      content_feedback, confidence_feedback,  │
│      all analysis breakdowns                 │
│  }                                           │
└────────────┬─────────────────────────────────┘
             │
             ↓
┌──────────────────────────────────────────────┐
│  interview_engine.py generate_tip()          │
│  (Only in practice mode)                     │
│                                              │
│  Generate contextual real-time feedback:     │
│  - If content_score < 40: "Add structure"    │
│  - If filler_count > 3: "Avoid um/uh"        │
│  - If confidence_score < 45: "Speak slower"  │
│  - If WPM > 180: "You're too fast"           │
│                                              │
│  OUTPUT: tip = "💡 Nice answer! Keep..."     │
└────────────┬─────────────────────────────────┘
             │
             ↓
┌──────────────────────────────────────────────┐
│  Store Answer in Database                    │
│  Answer model:                               │
│  - interview_id, question_number             │
│  - transcription, audio_path                 │
│  - content_score, confidence_score           │
│  - combined_score                            │
│  - feedback, tips                            │
└────────────┬─────────────────────────────────┘
             │
             ↓
┌──────────────────────────────────────────────┐
│  Return to Frontend (Real-time):             │
│  - Show transcribed text                     │
│  - Show scores                               │
│  - Show feedback                             │
│  - Show tip (if practice mode)               │
└──────────────────────────────────────────────┘
```

---

## 8. Files Requiring Fixes

### Priority 1: High Severity 🔴

**File 1**: `backend/models/interview_engine.py`
- **Lines**: 587-597
- **Issue**: Hardcoded `sample_resume` test data
- **Fix**: Remove or move to separate test fixtures
- **Time**: 5 min

**File 2**: `backend/models/interview_engine.py`
- **Lines**: 180-220
- **Issue**: Template string interpolation without validation
- **Fix**: Add validation, use type checking
- **Time**: 30 min

---

### Priority 2: Medium Severity 🟡

**File 3**: `backend/models/cv_reviewer.py`
- **Lines**: 60-100
- **Issue**: Hardcoded Pakistani phone/location format
- **Fix**: Make configurable, accept multiple formats
- **Time**: 20 min

**File 4**: `backend/models/resume_parser.py`
- **Lines**: 65-160
- **Issue**: Company name detection unreliable
- **Fix**: Improve filtering, add validation
- **Time**: 45 min

**File 5**: `backend/models/interview_engine.py`
- **Lines**: 157-165
- **Issue**: Job title matching is fragile
- **Fix**: Improve classification, use fuzzy matching
- **Time**: 30 min

**File 6**: `backend/models/answer_evaluator.py`
- **Lines**: 70-130
- **Issue**: Model answers not used in evaluation
- **Fix**: Integrate model answers into semantic similarity
- **Time**: 45 min

---

## 9. Quick Reference: Template Strings

All template strings are in `backend/models/interview_engine.py`:

| Template | Lines | Purpose | Uses Resume Data |
|----------|-------|---------|-----------------|
| Intro | 515-519 | Sample introduction | name, education, total_years, top_skills, job_title |
| Experience | 521-530 | Sample experience answer | company, total_years, top_skills |
| Projects | 532-537 | Sample project description | top_skills |
| Education | 539-543 | Sample education story | education, top_skills, job_title |
| Technical | 545-549 | Sample technical answer | top_skills |
| Behavioral | 551-556 | Sample behavioral answer | None (generic) |
| Job-specific | 558-562 | Sample job-specific answer | job_title |
| Closing | 564-568 | Sample closing answer | None (generic) |
| Fallback | 571-575 | Catch-all template | top_skills, job_title |

---

## 10. No Hardcoded "aneeza" References

**Search Result**: Comprehensive grep search across:
- ✅ All .py files in `backend/`, `training/`
- ✅ All .json files (interview_payload.json, etc.)
- ✅ All .html/.js files in `frontend/`
- ✅ All .bat files for setup

**Conclusion**: No "aneeza" references found. The codebase uses generic test data with names like "Ahmed Khan" and companies like "TechCorp".

---

## 11. Recommendations

### Immediate (Do First):
1. ✅ Remove hardcoded `sample_resume` test data from production paths
2. ✅ Add validation to template string interpolations
3. ✅ Make CV reviewer location-agnostic

### Short-term (Next Sprint):
4. ✅ Improve company name detection
5. ✅ Integrate model answers into evaluation
6. ✅ Standardize field handling across codebase

### Long-term (Roadmap):
7. ✅ Better job title classification (ML-based)
8. ✅ Multi-language support
9. ✅ Configurable interview templates
10. ✅ A/B testing framework for questions/scoring

---

## 12. Testing Checklist

- [ ] Test with resume missing name field
- [ ] Test with resume having 0 years experience
- [ ] Test with resume having non-Pakistani phone number
- [ ] Test with company name containing special characters
- [ ] Test with job titles not in template list
- [ ] Test with very short resume (< 150 words)
- [ ] Test with very long resume (> 900 words)
- [ ] Test with multiple companies in resume
- [ ] Test with no skills extracted
- [ ] Test with international university names

---

## Conclusion

The AI Interview Coach codebase has a well-structured pipeline from resume parsing through question generation to answer evaluation. However, **11 data mapping and template issues** have been identified, with **2 HIGH severity issues** requiring immediate attention:

1. **Hardcoded test data** that could leak into production
2. **Unvalidated template interpolation** that could produce malformed questions

The **flow is fundamentally sound**, but edge cases and validation need strengthening.

**Estimated fix time**: 3-4 hours for all issues.

---

*Analysis completed: 2026-08-31*  
*No "aneeza" references found in codebase.*
