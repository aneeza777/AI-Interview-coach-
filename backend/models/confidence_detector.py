"""
Confidence Detection Module
==========================
Analyzes voice audio to detect speaking confidence based on:
1. Speaking pace (words per minute)
2. Pitch variation (monotone vs dynamic)
3. Pause analysis (frequency and duration of silences)
4. Volume consistency (steady vs wavering)
5. Neural network classifier trained on confidence features

Uses librosa for audio feature extraction + trained PyTorch classifier.
"""

import json
import numpy as np
import librosa
import soundfile as sf
from pathlib import Path
from typing import Dict, List, Tuple


# ──────────────────────────────────────────────
# Trained confidence classifier (neural network)
# ──────────────────────────────────────────────
_CONFIDENCE_MODEL_PATH = Path(__file__).parent.parent.parent / "training" / "models_output" / "confidence_classifier"
_confidence_net = None
_scaler_params = None


def _load_confidence_net():
    """Load trained confidence classifier if available."""
    global _confidence_net, _scaler_params

    if _confidence_net is not None:
        return True

    model_file = _CONFIDENCE_MODEL_PATH / "confidence_net.pth"
    scaler_file = _CONFIDENCE_MODEL_PATH / "scaler_params.json"

    if not model_file.exists() or not scaler_file.exists():
        return False

    try:
        import torch
        import torch.nn as nn

        class ConfidenceNet(nn.Module):
            def __init__(self, input_dim=5, hidden_dim=64, num_classes=3):
                super().__init__()
                self.network = nn.Sequential(
                    nn.Linear(input_dim, hidden_dim), nn.ReLU(), nn.Dropout(0.2),
                    nn.Linear(hidden_dim, hidden_dim), nn.ReLU(), nn.Dropout(0.2),
                    nn.Linear(hidden_dim, 32), nn.ReLU(),
                    nn.Linear(32, num_classes),
                )
            def forward(self, x):
                return self.network(x)

        checkpoint = torch.load(str(model_file), map_location="cpu", weights_only=False)
        _confidence_net = ConfidenceNet(input_dim=5)
        _confidence_net.load_state_dict(checkpoint["model_state_dict"])
        _confidence_net.eval()

        with open(scaler_file, "r") as f:
            _scaler_params = json.load(f)

        print("[Confidence Detector] Trained neural network loaded.")
        return True
    except Exception as e:
        print(f"[Confidence Detector] Could not load trained model: {e}")
        return False


def _classify_confidence(features: List[float]) -> Dict:
    """Classify confidence using trained neural network."""
    if not _load_confidence_net():
        return None

    try:
        import torch

        # Normalize features using saved scaler params
        mean = np.array(_scaler_params["mean"])
        scale = np.array(_scaler_params["scale"])
        normalized = (np.array(features) - mean) / scale

        input_tensor = torch.FloatTensor(normalized).unsqueeze(0)

        with torch.no_grad():
            output = _confidence_net(input_tensor)
            probs = torch.softmax(output, dim=1)[0]
            predicted_class = torch.argmax(probs).item()

        labels = ["nervous", "moderate", "confident"]
        return {
            "nn_class": labels[predicted_class],
            "nn_confidence": float(probs[predicted_class].item()),
            "nn_probabilities": {labels[i]: round(float(probs[i].item()), 3) for i in range(3)},
        }
    except Exception as e:
        print(f"[Confidence Detector] NN classification failed: {e}")
        return None


# ──────────────────────────────────────────────
# Speaking rate estimation
# ──────────────────────────────────────────────
def _estimate_speaking_rate(audio_path: str, sr: int = 16000) -> Dict:
    """
    Estimate words per minute using energy-based syllable detection.
    Good speaking rate: 120-160 WPM for interviews.
    """
    y, sr = librosa.load(audio_path, sr=sr, mono=True)
    duration = librosa.get_duration(y=y, sr=sr)

    if duration < 1.0:
        return {"wpm": 0, "score": 0.0, "feedback": "Audio too short to analyze."}

    # Compute onset strength (detects speech syllables)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    onsets = librosa.onset.onset_detect(
        y=y, sr=sr,
        onset_envelope=onset_env,
        units="time",
        backtrack=True,
    )

    # Rough estimate: each onset ≈ one syllable, ~1.5 syllables per word
    estimated_words = len(onsets) / 1.5
    minutes = duration / 60.0
    wpm = estimated_words / minutes if minutes > 0 else 0

    # Score based on ideal WPM range (120-160)
    if 120 <= wpm <= 160:
        score = 0.9
        feedback = "Excellent speaking pace."
    elif 100 <= wpm < 120 or 160 < wpm <= 180:
        score = 0.68
        feedback = "Speaking pace is acceptable but could be better."
    elif 80 <= wpm < 100:
        score = 0.42
        feedback = "Speaking a bit slowly — try to maintain a natural pace."
    elif wpm > 180:
        score = 0.42
        feedback = "Speaking too fast — slow down for clarity."
    else:
        score = 0.2
        feedback = "Speaking pace is unusual — try to speak at a natural conversational rate."

    return {
        "wpm": round(wpm, 1),
        "score": round(score, 3),
        "feedback": feedback,
        "duration": round(duration, 2),
    }


# ──────────────────────────────────────────────
# Pitch variation analysis
# ──────────────────────────────────────────────
def _analyze_pitch_variation(audio_path: str, sr: int = 16000) -> Dict:
    """
    Analyze pitch (F0) variation. Confident speakers have dynamic pitch.
    Monotone speech suggests nervousness or lack of engagement.
    """
    y, sr = librosa.load(audio_path, sr=sr, mono=True)

    # Extract pitch using pyin (probabilistic YIN)
    f0, voiced_flag, voiced_probs = librosa.pyin(
        y, fmin=80, fmax=400, sr=sr
    )

    # Filter to voiced frames only
    voiced_f0 = f0[~np.isnan(f0)]

    if len(voiced_f0) < 10:
        return {
            "pitch_std": 0.0,
            "score": 0.3,
            "feedback": "Not enough voiced speech detected for pitch analysis.",
        }

    # Calculate pitch statistics
    pitch_mean = np.mean(voiced_f0)
    pitch_std = np.std(voiced_f0)
    pitch_range = np.max(voiced_f0) - np.min(voiced_f0)

    # Coefficient of variation (std/mean) normalized
    cv = pitch_std / pitch_mean if pitch_mean > 0 else 0

    # Score: higher variation = more confident (but not excessive)
    if 0.08 <= cv <= 0.25:
        score = 0.9
        feedback = "Good pitch variation — you sound dynamic and engaged."
    elif 0.05 <= cv < 0.08 or 0.25 < cv <= 0.35:
        score = 0.65
        feedback = "Moderate pitch variation — try adding more vocal emphasis."
    elif cv < 0.05:
        score = 0.4
        feedback = "Your voice sounds monotone — try varying your tone for emphasis."
    else:
        score = 0.5
        feedback = "Pitch variation is high — ensure it's intentional, not nervous."

    return {
        "pitch_mean": round(float(pitch_mean), 2),
        "pitch_std": round(float(pitch_std), 2),
        "pitch_range": round(float(pitch_range), 2),
        "pitch_cv": round(float(cv), 4),
        "score": round(score, 3),
        "feedback": feedback,
    }


# ──────────────────────────────────────────────
# Pause analysis
# ──────────────────────────────────────────────
def _analyze_pauses(audio_path: str, sr: int = 16000) -> Dict:
    """
    Detect pauses in speech. Confident speakers have fewer, shorter pauses.
    Frequent long pauses suggest uncertainty.
    """
    y, sr = librosa.load(audio_path, sr=sr, mono=True)

    # Compute RMS energy
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]

    # Define silence threshold (relative to max energy)
    threshold = np.max(rms) * 0.05
    is_silence = rms < threshold

    # Find silence segments
    silence_frames = np.where(is_silence)[0]
    hop_time = 512 / sr  # time per frame

    # Group consecutive silence frames into pauses
    pauses = []
    if len(silence_frames) > 0:
        current_start = silence_frames[0]
        current_length = 1

        for i in range(1, len(silence_frames)):
            if silence_frames[i] == silence_frames[i - 1] + 1:
                current_length += 1
            else:
                pause_duration = current_length * hop_time
                if pause_duration >= 0.3:  # Only count pauses >= 300ms
                    pauses.append(pause_duration)
                current_start = silence_frames[i]
                current_length = 1

        # Handle last segment
        pause_duration = current_length * hop_time
        if pause_duration >= 0.3:
            pauses.append(pause_duration)

    total_duration = librosa.get_duration(y=y, sr=sr)

    # Calculate pause metrics
    num_pauses = len(pauses)
    total_pause_time = sum(pauses)
    avg_pause_length = np.mean(pauses) if pauses else 0
    pause_ratio = total_pause_time / total_duration if total_duration > 0 else 0

    # Score based on pause metrics
    # Ideal: 2-5 pauses, < 20% silence ratio
    if num_pauses <= 3 and pause_ratio < 0.15:
        score = 0.9
        feedback = "Minimal pauses — you spoke fluently."
    elif num_pauses <= 6 and pause_ratio < 0.25:
        score = 0.68
        feedback = "Some pauses detected — mostly natural."
    elif num_pauses <= 10 and pause_ratio < 0.35:
        score = 0.48
        feedback = "Several pauses — try to prepare key points before speaking."
    else:
        score = 0.25
        feedback = "Many pauses detected — practice speaking more continuously."

    return {
        "num_pauses": num_pauses,
        "total_pause_time": round(float(total_pause_time), 2),
        "avg_pause_length": round(float(avg_pause_length), 2),
        "pause_ratio": round(float(pause_ratio), 3),
        "score": round(score, 3),
        "feedback": feedback,
    }


# ──────────────────────────────────────────────
# Volume consistency analysis
# ──────────────────────────────────────────────
def _analyze_volume_consistency(audio_path: str, sr: int = 16000) -> Dict:
    """
    Analyze volume/energy consistency. Confident speakers maintain
    steady volume; nervous speakers may trail off or fluctuate.
    """
    y, sr = librosa.load(audio_path, sr=sr, mono=True)

    # Compute RMS energy
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]

    # Filter out silence
    threshold = np.max(rms) * 0.1
    voiced_rms = rms[rms > threshold]

    if len(voiced_rms) < 10:
        return {"score": 0.3, "feedback": "Not enough audio for volume analysis."}

    # Coefficient of variation in volume
    mean_vol = np.mean(voiced_rms)
    std_vol = np.std(voiced_rms)
    cv = std_vol / mean_vol if mean_vol > 0 else 0

    # Score: lower CV = more consistent volume
    if cv < 0.3:
        score = 0.9
        feedback = "Very consistent volume — you sound steady and confident."
    elif cv < 0.5:
        score = 0.7
        feedback = "Mostly consistent volume with natural variation."
    elif cv < 0.7:
        score = 0.5
        feedback = "Volume varies quite a bit — try to maintain a steady level."
    else:
        score = 0.3
        feedback = "Volume is very inconsistent — project your voice evenly."

    return {
        "volume_mean": round(float(mean_vol), 4),
        "volume_std": round(float(std_vol), 4),
        "volume_cv": round(float(cv), 3),
        "score": round(score, 3),
        "feedback": feedback,
    }


# ──────────────────────────────────────────────
# Main confidence detection function
# ──────────────────────────────────────────────
def detect_confidence(audio_path: str) -> Dict:
    """
    Full confidence analysis from voice audio.

    Returns:
        {
            "confidence_score": float (0-100),
            "breakdown": {
                "speaking_rate": Dict,
                "pitch_variation": Dict,
                "pauses": Dict,
                "volume_consistency": Dict,
            },
            "feedback": str,
            "tips": List[str],
        }
    """
    try:
        # Run all analyses
        rate = _estimate_speaking_rate(audio_path)
        pitch = _analyze_pitch_variation(audio_path)
        pauses = _analyze_pauses(audio_path)
        volume = _analyze_volume_consistency(audio_path)

        # Weighted combination
        weights = {
            "speaking_rate": 0.25,
            "pitch_variation": 0.25,
            "pauses": 0.30,
            "volume_consistency": 0.20,
        }

        raw_score = (
            rate["score"] * weights["speaking_rate"]
            + pitch["score"] * weights["pitch_variation"]
            + pauses["score"] * weights["pauses"]
            + volume["score"] * weights["volume_consistency"]
        )

        # ── Penalties so weak/short takes don't default above 50 ──
        duration = rate.get("duration", 0)
        # Very short answers don't give enough signal to sound confident
        if duration < 4.0:
            raw_score *= 0.50
        elif duration < 8.0:
            raw_score *= 0.72
        elif duration < 12.0:
            raw_score *= 0.88
        # Lots of silence / hesitation relative to speaking
        if pauses.get("pause_ratio", 0) > 0.45:
            raw_score *= 0.75
        elif pauses.get("pause_ratio", 0) > 0.30:
            raw_score *= 0.88

        # ── Neural network classifier (if trained model available) ──
        nn_result = None
        features = [
            rate.get("wpm", 0),
            pitch.get("pitch_cv", 0),
            pauses.get("pause_ratio", 0),
            volume.get("volume_cv", 0),
            pauses.get("num_pauses", 0) / max(rate.get("duration", 1) / 60, 1),
        ]
        nn_result = _classify_confidence(features)

        # Blend NN score with heuristic score (70% NN if available, 30% heuristic)
        if nn_result and nn_result.get("nn_confidence", 0) > 0.5:
            # Map NN class to score: nervous=0.3, moderate=0.6, confident=0.9
            nn_score_map = {"nervous": 0.3, "moderate": 0.6, "confident": 0.9}
            nn_score = nn_score_map.get(nn_result["nn_class"], 0.5)
            raw_score = raw_score * 0.3 + nn_score * 0.7

        confidence_score = round(raw_score * 100, 1)

        # Overall feedback
        if confidence_score >= 80:
            overall = "You sound very confident! Great speaking style."
        elif confidence_score >= 60:
            overall = "You sound fairly confident with room for improvement."
        elif confidence_score >= 40:
            overall = "Your confidence could improve — practice will help."
        else:
            overall = "You sound nervous — don't worry, practice makes perfect!"

        # Collect tips
        tips = []
        if rate["score"] < 0.7:
            tips.append(rate["feedback"])
        if pitch["score"] < 0.7:
            tips.append(pitch["feedback"])
        if pauses["score"] < 0.7:
            tips.append(pauses["feedback"])
        if volume["score"] < 0.7:
            tips.append(volume["feedback"])

        if not tips:
            tips.append("Keep up the great speaking style!")

        return {
            "confidence_score": confidence_score,
            "breakdown": {
                "speaking_rate": rate,
                "pitch_variation": pitch,
                "pauses": pauses,
                "volume_consistency": volume,
                "nn_classification": nn_result,
            },
            "feedback": overall,
            "tips": tips,
        }

    except Exception as e:
        return {
            "confidence_score": 0,
            "breakdown": {},
            "feedback": f"Confidence analysis failed: {str(e)}",
            "tips": ["Ensure your audio is clear and contains speech."],
        }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python confidence_detector.py <path_to_audio>")
    else:
        result = detect_confidence(sys.argv[1])
        print(f"Confidence Score: {result['confidence_score']}/100")
        print(f"Feedback: {result['feedback']}")
        for tip in result["tips"]:
            print(f"  - {tip}")
