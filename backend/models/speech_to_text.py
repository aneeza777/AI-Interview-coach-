"""
Speech-to-Text Module
=====================
Converts spoken audio (from browser mic recordings) to text using
OpenAI's Whisper (open-source, runs locally).

Supports: .wav, .webm, .mp3, .ogg audio formats
"""

import os
import re
import tempfile
import whisper
from pathlib import Path
from typing import Optional, Dict


# ──────────────────────────────────────────────
# Model loading (lazy singleton)
# ──────────────────────────────────────────────
_whisper_model = None


def get_whisper_model(model_size: str = "small") -> whisper.Whisper:
    """
    Load Whisper model (cached after first load).

    Model sizes: tiny, base, small, medium, large
    - "small" gives much better accuracy for accented/mixed English
      (a bit slower than "base", but far fewer wrong/repeated words)
    """
    global _whisper_model
    if _whisper_model is None:
        print(f"[Speech-to-Text] Loading Whisper model '{model_size}'...")
        _whisper_model = whisper.load_model(model_size)
        print("[Speech-to-Text] Model loaded successfully.")
    return _whisper_model


# ──────────────────────────────────────────────
# Audio format conversion (if needed)
# ──────────────────────────────────────────────
def _ensure_compatible_format(audio_path: str) -> str:
    """
    Whisper works best with 16kHz mono WAV.
    Convert if necessary using soundfile + librosa.
    """
    ext = Path(audio_path).suffix.lower()

    # If already WAV, check sample rate
    if ext == ".wav":
        return audio_path

    # Convert to WAV using soundfile + librosa
    try:
        import librosa
        import soundfile as sf

        # Load audio at 16kHz mono
        audio_data, sample_rate = librosa.load(audio_path, sr=16000, mono=True)

        # Save as temp WAV
        temp_wav = tempfile.mktemp(suffix=".wav")
        sf.write(temp_wav, audio_data, 16000)
        return temp_wav

    except Exception as e:
        print(f"[Speech-to-Text] Warning: Could not convert {ext} to WAV: {e}")
        return audio_path


# ──────────────────────────────────────────────
# Main transcription function
# ──────────────────────────────────────────────
def _load_audio_array(audio_path: str) -> "np.ndarray":
    """
    Load any audio file into a Whisper-compatible numpy array.
    Uses soundfile for WAV and librosa fallback for other formats.
    Output: float32 array, mono, 16 kHz, normalized to [-1, 1].
    """
    import soundfile as sf
    import librosa
    import numpy as np

    try:
        # Fast path for WAV files (what the browser sends)
        audio, sr = sf.read(str(audio_path), dtype="float32")
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        if sr != 16000:
            audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
        return audio.astype("float32")
    except Exception:
        # Fallback for non-WAV formats
        audio, sr = librosa.load(str(audio_path), sr=16000, mono=True)
        return audio.astype("float32")


def _is_valid_transcription(text: str) -> bool:
    """
    Check if transcription looks valid (not corrupted/hallucinated).
    
    Flags suspicious patterns like:
    - Repeated single characters (m-m-m-m or mmmmmm)
    - All punctuation with no words
    - Less than 2 words
    - Too many repeated words (more than 50%)
    """
    if not text or len(text.strip()) < 2:
        return False
    
    text_lower = text.lower().strip()
    words = text_lower.split()
    
    # Too short
    if len(words) < 2:
        return False
    
    # Check for repeated single character pattern (m-m-m or mmmm)
    if re.search(r'^([a-z])-?\1(-?\1)+', text_lower):
        return False
    if re.search(r'^([a-z])\1{3,}', text_lower):  # mmmmmm pattern
        return False
    
    # Check for repeated word sequences (and and and, the the the, etc)
    for i in range(len(words) - 2):
        if words[i] == words[i+1] == words[i+2]:
            # Same word repeated 3+ times in a row
            if words[i] in ['and', 'the', 'a', 'or', 'but', 'is', 'are', 'be', 'been']:
                return False  # Common words repeated = corrupted
            # Even for other words, 3+ repetitions is suspicious
            return False
    
    # Check if mostly punctuation
    alpha_ratio = sum(1 for c in text if c.isalpha()) / len(text) if text else 0
    if alpha_ratio < 0.3:
        return False
    
    # Check for excessive repetition of single words
    if len(words) > 3:
        # Count word frequency (only words longer than 1 character)
        word_counts = {}
        for word in words:
            if len(word) > 1 and word not in ['and', 'the', 'of', 'is', 'a', 'in', 'to', 'for']:
                word_counts[word] = word_counts.get(word, 0) + 1
        
        if word_counts:
            max_count = max(word_counts.values())
            max_ratio = max_count / len(words)
            if max_ratio > 0.4:  # More than 40% same content word is suspicious
                return False
    
    return True


def _sanitize_transcription(text: str) -> str:
    """
    Sanitize obviously corrupted transcriptions.
    Returns original if valid, otherwise returns placeholder.
    """
    if _is_valid_transcription(text):
        return text.strip()
    
    # Return a generic placeholder for invalid transcriptions
    return "[Transcription error - could not capture speech clearly. Please try again.]"


def transcribe_audio(
    audio_path: str,
    model_size: str = "small",
    language: Optional[str] = "en",
    prompt: Optional[str] = None,
) -> Dict:
    """
    Transcribe audio file to text using Whisper.

    Args:
        audio_path: Path to the audio file.
        model_size: Whisper model size (tiny/base/small/medium/large).
        language: Language code (None for auto-detect, "en" for English).
        prompt: Optional text prompt to guide transcription (e.g., the interview question).

    Returns:
        {
            "text": str,             # Full transcribed text
            "segments": List[Dict],  # Timestamped segments
            "language": str,         # Detected/specified language
            "duration": float,       # Audio duration in seconds
        }
    """
    import traceback

    model = get_whisper_model(model_size)

    try:
        # Load audio as numpy array (16 kHz mono) without ffmpeg
        audio_data = _load_audio_array(audio_path)
        duration = float(len(audio_data) / 16000)

        # Run transcription on the audio array
        options = {
            "language": language,
            "task": "transcribe",
            "verbose": False,
            # Prevent Whisper from repeating the same phrase across segments
            "condition_on_previous_text": False,
            # Temperature sampling to reduce hallucination
            "temperature": 0.0,
            "compression_ratio_threshold": 2.4,
            "logprob_threshold": -1.0,
            "no_speech_threshold": 0.6,
        }
        if prompt:
            options["initial_prompt"] = prompt

        result = model.transcribe(audio_data, **options)

        # Extract segments with timestamps
        segments = []
        for seg in result.get("segments", []):
            segments.append({
                "start": round(seg["start"], 2),
                "end": round(seg["end"], 2),
                "text": seg["text"].strip(),
            })

        # Prefer actual audio duration; fall back to last segment
        if not duration and segments:
            duration = segments[-1]["end"]

        # Sanitize transcription text (detect/reject corrupted output like "m-m-m-m")
        sanitized_text = _sanitize_transcription(result["text"].strip())

        return {
            "text": sanitized_text,
            "segments": segments,
            "language": result.get("language", language or "unknown"),
            "duration": round(duration, 2),
        }

    except Exception as e:
        print(f"[Speech-to-Text] Transcription error: {e}")
        traceback.print_exc()
        raise RuntimeError(f"Transcription failed: {e}")


# ──────────────────────────────────────────────
# Quick validation: check if audio has speech
# ──────────────────────────────────────────────
def is_speech_present(audio_path: str, min_duration: float = 1.0) -> bool:
    """Check if audio file has at least min_duration seconds of audio."""
    try:
        import librosa
        duration = librosa.get_duration(path=audio_path)
        return duration >= min_duration
    except Exception:
        return True  # If we can't check, assume it's valid


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python speech_to_text.py <path_to_audio_file>")
    else:
        result = transcribe_audio(sys.argv[1])
        print(f"Text: {result['text']}")
        print(f"Duration: {result['duration']}s")
        print(f"Language: {result['language']}")
