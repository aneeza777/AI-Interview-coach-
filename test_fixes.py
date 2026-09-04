#!/usr/bin/env python3
"""
Test script to verify resume parsing and interview question generation fixes.
Tests that phone numbers, emails, and contact info are not extracted as names
or company names.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from models.resume_parser import extract_name, _is_valid_name, _looks_like_company
from models.interview_engine import _sanitize_name, _pick_valid_company, generate_model_answer

# Test cases for name validation
print("=" * 60)
print("Testing Name Validation")
print("=" * 60)

test_names = [
    ("Aneeza Khan", True, "Valid person name"),
    ("contact 0332", False, "Contact info - should reject"),
    ("0332", False, "Phone number - should reject"),
    ("+92-300-1234567", False, "Full phone - should reject"),
    ("email@example.com", False, "Email - should reject"),
    ("Phone: 1234567", False, "Phone header - should reject"),
    ("", False, "Empty string - should reject"),
    ("A", False, "Too short - should reject"),
    ("John Doe", True, "Valid two-word name"),
    ("Dr. Sarah Smith", True, "Valid three-word name"),
    ("123456", False, "All numbers - should reject"),
]

print("\nTesting _is_valid_name():")
for name, expected, description in test_names:
    result = _is_valid_name(name)
    status = "✓" if result == expected else "✗"
    print(f"{status} {description:40} | Input: '{name}' | Result: {result}")

# Test cases for company validation
print("\n" + "=" * 60)
print("Testing Company Name Validation")
print("=" * 60)

test_companies = [
    ("TechCorp", True, "Valid company name"),
    ("Google Inc", True, "Valid company with Inc"),
    ("0332", False, "Phone number - should reject"),
    ("+92-300-1234567", False, "Full phone - should reject"),
    ("email@company.com", False, "Email - should reject"),
    ("Engineer Developer", False, "Job titles - should reject"),
    ("University College", False, "Education - should reject"),
    ("Morgan Stanley Investment Bank", False, "Too many words"),
    ("Microsoft", True, "Valid single-word company"),
]

print("\nTesting _looks_like_company():")
for company, expected, description in test_companies:
    result = _looks_like_company(company)
    status = "✓" if result == expected else "✗"
    print(f"{status} {description:40} | Input: '{company}' | Result: {result}")

# Test sanitization
print("\n" + "=" * 60)
print("Testing Name Sanitization in Interview Engine")
print("=" * 60)

test_sanitize = [
    ("Aneeza Khan", "Aneeza Khan", "Valid name should pass through"),
    ("contact 0332", "the candidate", "Contact info should become default"),
    ("0332", "the candidate", "Phone should become default"),
    (None, "the candidate", "None should become default"),
]

print("\nTesting _sanitize_name():")
for input_name, expected, description in test_sanitize:
    result = _sanitize_name(input_name)
    status = "✓" if result == expected else "✗"
    print(f"{status} {description:40} | Input: {input_name} | Result: {result}")

# Test company picking
print("\n" + "=" * 60)
print("Testing Company Selection from Mixed Lists")
print("=" * 60)

test_company_lists = [
    (["TechCorp", "Google"], "TechCorp", "Valid companies - picks first"),
    (["0332", "contact", "TechCorp"], "TechCorp", "Mixed with invalid - picks valid"),
    (["contact 0332", "+92-300", "phone"], None, "All invalid - returns None"),
    (["Google Inc"], "Google Inc", "Single valid company"),
    (["email@company.com", "LinkedIn"], "LinkedIn", "Email before valid"),
]

print("\nTesting _pick_valid_company():")
for companies, expected, description in test_company_lists:
    result = _pick_valid_company(companies)
    status = "✓" if result == expected else "✗"
    print(f"{status} {description:40} | Result: {result}")

# Test model answer generation with bad data
print("\n" + "=" * 60)
print("Testing Model Answer Generation with Bad Data")
print("=" * 60)

resume_with_bad_name = {
    "name": "contact 0332",  # Bad name
    "skills": ["Python", "React"],
    "experience": {"companies": ["0332", "TechCorp"], "total_years": 2},
    "education": ["BS Computer Science"],
}

resume_with_good_name = {
    "name": "Aneeza Khan",  # Good name
    "skills": ["Python", "React"],
    "experience": {"companies": ["0332", "TechCorp"], "total_years": 2},
    "education": ["BS Computer Science"],
}

print("\nGenerating introduction answers:")
question = {"type": "introduction"}

print("\nWith bad name 'contact 0332':")
bad_answer = generate_model_answer(question, resume_with_bad_name, "Software Engineer")
print(f"  Answer: {bad_answer[:100]}...")
if "the candidate" in bad_answer or "contact" not in bad_answer:
    print("  ✓ Correctly rejected bad name")
else:
    print("  ✗ Failed to reject bad name")

print("\nWith good name 'Aneeza Khan':")
good_answer = generate_model_answer(question, resume_with_good_name, "Software Engineer")
print(f"  Answer: {good_answer[:100]}...")
if "Aneeza Khan" in good_answer:
    print("  ✓ Correctly used valid name")
else:
    print("  ✗ Failed to use valid name")

print("\n" + "=" * 60)
print("All tests completed!")
print("=" * 60)
