#!/usr/bin/env python3
"""Integration test: Verify complete fix pipeline."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from models.resume_parser import extract_name, _is_valid_name
from models.interview_engine import generate_model_answer, _sanitize_name
from models.speech_to_text import transcribe_audio, _is_valid_transcription, _sanitize_transcription

print("=" * 70)
print("INTEGRATION TEST: Complete Fix Pipeline")
print("=" * 70)

# Simulate a corrupted resume that was parsed before the fix
print("\n1. CORRUPTED RESUME DATA (from database)")
print("-" * 70)
corrupted_resume_data = {
    "name": "github.com/aneeza777",
    "education": ["Computer Science Graduate | Flutter & Mobile App Development"],
    "skills": ["Python", "JavaScript", "Machine Learning"],
    "experience": {
        "companies": ["Post-Quantum Cryptography Rawalpindi"],
        "total_years": 0
    }
}

print(f"Name in DB: '{corrupted_resume_data['name']}'")
print(f"Is valid name? {_is_valid_name(corrupted_resume_data['name'])}")
print(f"Sanitized name: '{_sanitize_name(corrupted_resume_data['name'])}'")

# Test model answer generation
print("\n2. MODEL ANSWER GENERATION")
print("-" * 70)
question = {
    "number": 1,
    "question": "Could you please introduce yourself?",
    "type": "introduction",
    "expected_keywords": ["name", "education", "experience"]
}

model_answer = generate_model_answer(
    question=question,
    resume_data=corrupted_resume_data,
    job_title="Software Engineer"
)

print(f"Generated Model Answer:\n{model_answer}")
print()
if "github.com" in model_answer.lower():
    print("❌ FAIL: GitHub URL still in model answer!")
else:
    print("✅ PASS: GitHub URL filtered out!")

# Test transcription validation
print("\n3. TRANSCRIPTION VALIDATION")
print("-" * 70)
corrupted_transcription = (
    "I am a student of the University of Toronto, and I am a professor of the University of Toronto. "
    "I am a student of the University of Toronto, and I am a student of the University of Toronto. "
    "and and and and and and and and and and and Bye."
)

print(f"Transcription length: {len(corrupted_transcription)} chars, {len(corrupted_transcription.split())} words")
print()

is_valid = _is_valid_transcription(corrupted_transcription)
print(f"Is valid transcription? {is_valid}")

sanitized = _sanitize_transcription(corrupted_transcription)
print(f"Sanitized result: '{sanitized}'")

if is_valid:
    print("❌ FAIL: Corrupted transcription not detected!")
else:
    print("✅ PASS: Corrupted transcription correctly flagged as invalid!")

# Summary
print("\n" + "=" * 70)
print("INTEGRATION TEST SUMMARY")
print("=" * 70)
github_url_fixed = "github.com" not in model_answer.lower()
transcription_fixed = not is_valid

if github_url_fixed and transcription_fixed:
    print("✅ ALL FIXES WORKING - Both issues are resolved!")
else:
    if not github_url_fixed:
        print("❌ GitHub URL still appearing in model answers")
    if not transcription_fixed:
        print("❌ Corrupted transcriptions not being detected")
