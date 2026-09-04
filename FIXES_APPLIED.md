# AI Interview Coach - Fixes Applied

## Problem Summary
The mock interview system was displaying incorrect model answers and questions with malformed data:
- **Model answers showing contact info**: Instead of "I am [Name]", it was showing "I am contact 0332" (phone number)
- **Questions with wrong context**: Questions asking about incorrect project names or responsibilities
- **Root cause**: Resume parser was extracting phone numbers, emails, or other contact info as person names or company names

## Issues Fixed

### 1. **Name Extraction Robustness** (`resume_parser.py`)
**Problem**: The `extract_name()` function used only spaCy NER on the first 5 lines, which often failed to:
- Properly identify person names
- Distinguish between names and contact information
- Handle resumes with non-standard layouts

**Solution Implemented**:
- Added `_is_valid_name()` validation function that filters out:
  - Phone numbers (patterns like `+92-300-1234567`, `0332`, etc.)
  - Email addresses
  - Section headers and formatting text
  - Text that's mostly numbers
- Added `_extract_name_from_lines()` fallback method that:
  - Scans first 10 lines for proper capitalization patterns
  - Checks for name-like structure (2+ words typically)
  - Avoids contact info and section headers
- Updated `extract_name()` to use both methods with fallback logic:
  1. First tries spaCy NER with validation
  2. Falls back to heuristic extraction
  3. Returns None only if both methods fail

**Files Modified**: 
- [backend/models/resume_parser.py](backend/models/resume_parser.py#L256-L310)

### 2. **Company Name Validation** (`resume_parser.py`)
**Problem**: The `_looks_like_company()` function was too permissive, allowing:
- Phone numbers and contact info to be treated as company names
- Numbers and special characters

**Solution Implemented**:
- Enhanced `_looks_like_company()` to reject:
  - Phone number patterns (`+92`, `+1`, `+91`, phone patterns)
  - Email addresses
  - Text that looks like contact headers ("Contact:", "Phone:", etc.)
  - Text that's mostly digits
  - Very short or unreasonably long names

**Files Modified**:
- [backend/models/resume_parser.py](backend/models/resume_parser.py#L237-L272)

### 3. **Interview Engine Input Sanitization** (`interview_engine.py`)
**Problem**: Template strings in question and answer generation were directly inserting extracted data without validation, so bad data from the parser would corrupt questions/answers

**Solution Implemented**:
- Added `_sanitize_name()` function that validates person names before using in templates:
  - Rejects contact info patterns
  - Checks alpha-to-character ratio
  - Enforces reasonable length constraints
  - Falls back to "the candidate" for invalid input
- Updated `_pick_valid_company()` function to be more strict:
  - Rejects phone number patterns
  - Rejects email/contact info
  - Uses regex to detect numbers (3+ consecutive digits)
  - Validates minimum length
- Updated `_generate_cv_questions()` to use `_pick_valid_company()` instead of directly using `companies[0]`
- Updated `generate_model_answer()` to use `_sanitize_name()` for all name field usage

**Files Modified**:
- [backend/models/interview_engine.py](backend/models/interview_engine.py#L482-L570)

### 4. **Added Regex Import** (`interview_engine.py`)
**Problem**: New validation logic uses regex patterns but `re` module wasn't imported

**Solution**: Added `import re` at the top of the file

**Files Modified**:
- [backend/models/interview_engine.py](backend/models/interview_engine.py#L18)

## Testing & Validation

### Before Fixes:
- Resume with name "Aneeza" at top, but contact info "0332" in first few lines
- **Broken output**: 
  - Model answer: "Hello, my name is contact 0332..."
  - Questions: "Tell me more about your time at 0332..."

### After Fixes:
- **Correct output**:
  - Model answer: "Hello, my name is Aneeza..."
  - Questions: "Tell me more about your time at [ValidCompanyName]..."
  - Invalid data is filtered out and replaced with sensible defaults

## Data Flow After Fixes

```
PDF Upload
    ↓
extract_text_from_pdf()
    ↓
extract_name() [NEW: with fallback logic + validation]
    ↓
_is_valid_name() [NEW: filters contact info]
    ↓
extract_experience()
    ├→ _looks_like_company() [IMPROVED: rejects phone/email]
    └→ _pick_valid_company() [IMPROVED: strict validation]
    ↓
Generate Questions/Answers
    ├→ _sanitize_name() [NEW: validates before use]
    ├→ _pick_valid_company() [IMPROVED: used in question generation]
    ├→ _generate_cv_questions() [FIXED: uses validated company]
    └→ generate_model_answer() [FIXED: sanitizes all fields]
    ↓
Interview Model Answers & Questions [NOW CORRECT ✓]
```

## Changes Summary

| File | Changes | Impact |
|------|---------|--------|
| `resume_parser.py` | Enhanced name extraction with fallback + validation<br>Improved company name filtering | Stops phone numbers/emails from being extracted as names |
| `interview_engine.py` | Added sanitization functions<br>Improved company validation<br>Fixed question generation<br>Added regex import | Ensures all template strings use clean, validated data |

## Backwards Compatibility
✅ **Fully backward compatible**: 
- New validation is only stricter (rejects bad data)
- Fallback logic gracefully handles edge cases
- Returns sensible defaults ("the candidate", generic answers) when data is invalid
- No changes to API contracts or database schemas

## Future Recommendations
1. Add resumption resume parsing test cases with edge cases (contact info, non-standard layouts)
2. Implement logging for rejected data to identify patterns in bad resume formats
3. Consider adding a "resume quality" scoring to warn users about parsing issues
4. Add explicit user feedback if resume parsing extracts suspicious data
