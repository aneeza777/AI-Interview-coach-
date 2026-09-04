#!/usr/bin/env python3
"""Test with exact transcription from screenshot."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from models.speech_to_text import _is_valid_transcription

# Exact transcription from the screenshot
screenshot_text = "I am a student of the University of Toronto, and I am a professor of the University of Toronto. I am a student of the University of Toronto, and I am a student of the University of Toronto. and and and and and and and and and and and Bye."

print("Testing exact transcription from screenshot:")
print(f"Text: {screenshot_text}")
print()

result = _is_valid_transcription(screenshot_text)
print(f"Is valid: {result}")
print()

if not result:
    print("✅ CORRECTLY DETECTED AS CORRUPTED")
    print("Reason: Repeated 'and and and and and and and and and and and' sequence detected")
else:
    print("❌ FAILED TO DETECT CORRUPTION")
