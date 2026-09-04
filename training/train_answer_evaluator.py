"""
Train Answer Evaluator Model
==============================
Fine-tunes sentence-transformers (all-MiniLM-L6-v2) on interview answer
quality data using contrastive learning.

The model learns to:
- Give high similarity to (question, good_answer) pairs
- Give low similarity to (question, poor_answer) pairs

After training, saved to models_output/answer_evaluator/
"""

import os
import json
import random
import torch
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer, InputExample, losses
from sentence_transformers.evaluation import EmbeddingSimilarityEvaluator
from torch.utils.data import DataLoader


# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
BASE_MODEL = "all-MiniLM-L6-v2"  # 22M params, fast
DATA_PATH = Path(__file__).parent / "data" / "answer_evaluation_dataset.json"
OUTPUT_DIR = Path(__file__).parent / "models_output" / "answer_evaluator"


def load_and_prepare_data():
    """
    Convert answer evaluation data into training pairs:
    - (question + context, good_answer) → high similarity
    - (question + context, poor_answer) → low similarity
    """
    print("Loading dataset...")
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    print(f"  Loaded {len(raw_data)} samples")

    train_examples = []

    for item in raw_data:
        question = item["question"]
        answer = item["answer"]
        keywords = item.get("keywords", [])
        quality = item.get("quality_score", 2.5)

        # Normalize quality to 0-1 range (original is 0-5)
        similarity = quality / 5.0

        # Create training example: (question_context, answer, similarity)
        # The model learns that good answers should be similar to the question context
        question_context = question + " " + " ".join(keywords[:5])

        train_examples.append(InputExample(
            texts=[question_context, answer],
            label=similarity,
        ))

        # Also add negative examples by pairing with unrelated questions
        # This helps the model distinguish relevant from irrelevant answers
        if quality < 2.0:
            # Poor answer: pair with a different question to create a strong negative
            other_questions = [d["question"] for d in raw_data if d["question"] != question]
            if other_questions:
                random_q = random.choice(other_questions)
                train_examples.append(InputExample(
                    texts=[random_q + " " + " ".join(keywords[:3]), answer],
                    label=0.1,  # Very low similarity expected
                ))

    return train_examples


def train():
    """Main training loop."""
    print("=" * 60)
    print("  Training Answer Evaluator (sentence-transformers)")
    print("=" * 60)

    # ── Load model ──
    print(f"\nLoading base model: {BASE_MODEL}")
    model = SentenceTransformer(BASE_MODEL)

    # ── Prepare data ──
    examples = load_and_prepare_data()

    # Shuffle
    random.shuffle(examples)

    # Train/val split
    split_idx = int(len(examples) * 0.85)
    train_examples = examples[:split_idx]
    val_examples = examples[split_idx:]

    print(f"  Train pairs: {len(train_examples)}")
    print(f"  Val pairs:   {len(val_examples)}")

    # ── DataLoader ──
    train_dataloader = DataLoader(
        train_examples,
        shuffle=True,
        batch_size=16,
    )

    # ── Loss function: CosineSimilarityLoss ──
    # Learns to predict cosine similarity between sentence pairs
    train_loss = losses.CosineSimilarityLoss(model=model)

    # ── Evaluator ──
    if val_examples:
        val_sentences1 = [e.texts[0] for e in val_examples]
        val_sentences2 = [e.texts[1] for e in val_examples]
        val_scores = [e.label for e in val_examples]

        evaluator = EmbeddingSimilarityEvaluator(
            val_sentences1,
            val_sentences2,
            val_scores,
            name="interview-val",
        )
    else:
        evaluator = None

    # ── Train ──
    output_path = str(OUTPUT_DIR / "final")
    os.makedirs(output_path, exist_ok=True)

    print("\n🚀 Starting training...")
    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        evaluator=evaluator,
        epochs=10,
        warmup_steps=int(len(train_dataloader) * 0.1),
        optimizer_params={"lr": 2e-5},
        output_path=output_path,
        evaluation_steps=max(1, len(train_dataloader) // 5),
        save_best_model=True,
        show_progress_bar=True,
    )

    # ── Save metrics ──
    metrics = {
        "base_model": BASE_MODEL,
        "num_train_pairs": len(train_examples),
        "num_epochs": 10,
        "learning_rate": 2e-5,
    }

    with open(os.path.join(output_path, "training_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    # ── Test ──
    print("\n🧪 Testing similarity scores...")
    test_model = SentenceTransformer(output_path)

    test_pairs = [
        (
            "Explain your experience with Python project developed",
            "I have 4 years of experience with Python. I built several web applications using Django and FastAPI.",
        ),
        (
            "Explain your experience with Python project developed",
            "I like pizza and movies.",
        ),
        (
            "How do you handle tight deadlines prioritize",
            "I break down work into priorities, communicate with stakeholders, and focus on core features first.",
        ),
        (
            "How do you handle tight deadlines prioritize",
            "I don't really know, I just try to work harder maybe.",
        ),
    ]

    for q, a in test_pairs:
        embeddings = test_model.encode([q, a])
        similarity = np.dot(embeddings[0], embeddings[1]) / (
            np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
        )
        print(f"  Q: {q[:60]}...")
        print(f"  A: {a[:60]}...")
        print(f"  Similarity: {similarity:.3f}")
        print()

    print("✅ Answer evaluator training complete!")
    print(f"   Model saved to: {output_path}")
    return metrics


if __name__ == "__main__":
    train()
