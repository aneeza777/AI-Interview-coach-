"""
Kaggle Datasets Processor for AI Interview Coach
=================================================
Processes user's downloaded Kaggle datasets:
1. Mock_interview_questions.json (5,000 in-depth domain questions & model answers)
2. hr_interview_questions_dataset.json (2.5M multi-role HR & behavioral questions)

Extracts balanced, high-quality samples for:
- Question Generator (FLAN-T5)
- Answer Evaluator (Sentence-Transformers)
"""

import os
import json
import random
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True, parents=True)

mock_file = BASE_DIR / "Mock_interview_questions.json"
hr_file = BASE_DIR / "hr_interview_questions_dataset.json"

qg_samples = []
ae_samples = []

# ── 1. Process Mock_interview_questions.json (All 5,000 questions) ──
if mock_file.exists():
    print(f"Loading {mock_file.name}...", flush=True)
    with open(mock_file, "r", encoding="utf-8") as f:
        mock_data = json.load(f)
        questions_list = mock_data.get("questions", [])

    print(f"  Found {len(questions_list)} detailed mock interview questions.", flush=True)
    for q_item in questions_list:
        q_text = q_item.get("question", "").strip()
        ans_text = q_item.get("answer", "").strip()
        field = q_item.get("field", "General Field")
        subfield = q_item.get("subfield", "")
        tier = q_item.get("tier", "intermediate")

        if q_text:
            context = f"Domain: {field} | Specialization: {subfield} | Difficulty: {tier}"
            qg_samples.append({
                "context": context,
                "question": q_text,
                "category": field,
                "source": "kaggle_mock_interviews"
            })

            if ans_text:
                ae_samples.append({
                    "question": q_text,
                    "answer": ans_text,
                    "keywords": [field.lower(), subfield.lower(), "methodology"],
                    "quality_score": 4.8,
                    "quality_label": "excellent"
                })

# ── 2. Process hr_interview_questions_dataset.json (Streaming top 20,000 diverse samples) ──
if hr_file.exists():
    print(f"\nStreaming high-quality samples from {hr_file.name} (1.14 GB)...", flush=True)
    hr_count = 0
    max_hr_samples = 20000

    with open(hr_file, "r", encoding="utf-8") as f:
        # Stream read in 8MB chunks to stay fast and memory-efficient
        chunk_size = 1024 * 1024 * 8
        buffer = ""

        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            buffer += chunk

            items = buffer.split('  },\n  {')
            buffer = items.pop() # Keep the last incomplete item in buffer

            for item in items:
                clean = item.strip()
                if not clean.startswith('{'):
                    clean = '{' + clean
                if not clean.endswith('}'):
                    clean = clean + '}'
                try:
                    record = json.loads(clean)
                    q = record.get("question", "").strip()
                    role = record.get("role", "Professional")
                    cat = record.get("category", "Behavioral")
                    ans = record.get("ideal_answer", "").strip()
                    kws = record.get("keywords", [])
                    diff = record.get("difficulty", "Medium")
                    exp = record.get("experience", "")

                    if q:
                        qg_samples.append({
                            "context": f"Candidate Role: {role} | Category: {cat} | Experience: {exp}",
                            "question": q,
                            "category": cat,
                            "source": "kaggle_hr_dataset"
                        })

                        if ans:
                            ae_samples.append({
                                "question": q,
                                "answer": ans,
                                "keywords": kws if isinstance(kws, list) else [],
                                "quality_score": 4.7 if diff.lower() == "hard" else 4.5,
                                "quality_label": "excellent"
                            })

                        hr_count += 1
                        if hr_count >= max_hr_samples:
                            break
                except Exception:
                    continue

            if hr_count >= max_hr_samples:
                break

    print(f"  Streamed {hr_count} real multi-role HR questions.", flush=True)

# ── 3. Shuffle & Save ──
random.shuffle(qg_samples)
random.shuffle(ae_samples)

print(f"\nTotal Merged Question Generation Samples: {len(qg_samples):,}")
print(f"Total Merged Answer Evaluation Samples: {len(ae_samples):,}")

# Save to training data folder
for name in ["qg_dataset.json", "question_generation_dataset.json"]:
    with open(DATA_DIR / name, "w", encoding="utf-8") as f:
        json.dump(qg_samples, f, indent=2, ensure_ascii=False)

for name in ["ae_dataset.json", "answer_evaluation_dataset.json"]:
    with open(DATA_DIR / name, "w", encoding="utf-8") as f:
        json.dump(ae_samples, f, indent=2, ensure_ascii=False)

print(f"\nSUCCESS: Datasets processed and saved in {DATA_DIR}")
