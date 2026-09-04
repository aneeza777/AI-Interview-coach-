#!/usr/bin/env python3
"""Quick test for URL filtering and improved transcription validation."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from models.resume_parser import _is_valid_name
from models.interview_engine import _sanitize_name
from models.speech_to_text import _is_valid_transcription

print("=" * 70)
print("URL/Web Link Filtering Test - resume_parser.py")
print("=" * 70)

url_tests = [
    ("Aneeza Khan", True),
    ("github.com/aneeza777", False),
    ("linkedin.com/in/john", False),
    ("www.mysite.com", False),
    ("http://example.com", False),
    ("John@example.io", False),
    ("John Doe", True),
    ("Dr Sarah Smith", True),
]

print("\nTesting _is_valid_name() from resume_parser:")
for name, expected in url_tests:
    result = _is_valid_name(name)
    status = "✓" if result == expected else "✗"
    print(f"{status} {name:30} | Expected: {expected}, Got: {result}")

print("\n" + "=" * 70)
print("URL Filtering in Model Answers - interview_engine.py")
print("=" * 70)

sanitize_tests = [
    ("Aneeza Khan", "Aneeza Khan", "Valid name should pass"),
    ("github.com/aneeza777", "the candidate", "GitHub URL should be rejected"),
    ("linkedin.com/in/john", "the candidate", "LinkedIn URL should be rejected"),
    ("john@example.com", "the candidate", "Email domain should be rejected"),
    ("John Doe", "John Doe", "Valid name should pass"),
]

print("\nTesting _sanitize_name() from interview_engine:")
for input_name, expected, description in sanitize_tests:
    result = _sanitize_name(input_name)
    status = "✓" if result == expected else "✗"
    print(f"{status} {description:45} | Got: {result}")

print("\n" + "=" * 70)
print("Corrupted Transcription Detection Test")
print("=" * 70)

transcription_tests = [
    ("I am a software engineer with 5 years experience", True, "Valid normal speech"),
    ("m-m-m-m-m-m-m-m-m", False, "Repeated m pattern"),
    ("mmmmmmmmmmmmmm", False, "Repeated m without dash"),
    ("and and and and and and and and and", False, "Repeated 'and'"),
    ("the the the the the the", False, "Repeated 'the'"),
    ("I am a student of the University of Toronto and I am a professor of the University of Toronto and I am a student", False, "Over-repeated phrases (mimics screenshot)"),
    ("I have five years of experience", True, "Valid speech"),
    ("University of Toronto University of Toronto", False, "Same phrase repeated"),
]

print("\nTesting _is_valid_transcription():")
for text, expected, description in transcription_tests:
    result = _is_valid_transcription(text)
    status = "✓" if result == expected else "✗"
    display_text = text[:50] + "..." if len(text) > 50 else text
    print(f"{status} {description:45} | Result: {result}")
    if result != expected:
        print(f"    Text: '{display_text}'")

print("\n" + "=" * 70)
print("All tests completed!")
print("=" * 70)

