"""
Train Question Generator Model
===============================
Fine-tunes google/flan-t5-small (80M params) on interview question data
using LoRA (Parameter-Efficient Fine-Tuning).

Input:  Resume context + job title
Output: Interview question

After training, the model is saved to models_output/question_generator/
and loaded by the backend for inference.
"""

import os
import json
import torch
from pathlib import Path
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer,
    DataCollatorForSeq2Seq,
)
from peft import LoraConfig, get_peft_model, TaskType


# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
BASE_MODEL = "google/flan-t5-small"  # 80M params, fast to train
DATA_PATH = Path(__file__).parent / "data" / "question_generation_dataset.json"
OUTPUT_DIR = Path(__file__).parent / "models_output" / "question_generator"
MAX_INPUT_LEN = 256
MAX_OUTPUT_LEN = 128


def load_and_prepare_data():
    """Load dataset and format for T5 training."""
    print("Loading dataset...")
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    print(f"  Loaded {len(raw_data)} samples")

    # Format: input = "Generate an interview question for: {context}"
    #          output = the question
    formatted = []
    for item in raw_data:
        input_text = f"Generate an interview question for: {item['context']}"
        output_text = item["question"]
        formatted.append({
            "input_text": input_text,
            "output_text": output_text,
        })

    return formatted


def tokenize_data(examples, tokenizer):
    """Tokenize input/output pairs."""
    inputs = tokenizer(
        examples["input_text"],
        max_length=MAX_INPUT_LEN,
        truncation=True,
        padding="max_length",
    )
    outputs = tokenizer(
        examples["output_text"],
        max_length=MAX_OUTPUT_LEN,
        truncation=True,
        padding="max_length",
    )

    inputs["labels"] = outputs["input_ids"]
    return inputs


def train():
    """Main training loop."""
    print("=" * 60)
    print("  Training Question Generator (FLAN-T5 + LoRA)")
    print("=" * 60)

    # ── Load tokenizer and model ──
    print(f"\nLoading base model: {BASE_MODEL}")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    model = AutoModelForSeq2SeqLM.from_pretrained(BASE_MODEL)

    # ── Apply LoRA (efficient fine-tuning) ──
    print("Applying LoRA configuration...")
    lora_config = LoraConfig(
        task_type=TaskType.SEQ_2_SEQ_LM,
        r=16,                          # LoRA rank
        lora_alpha=32,                 # scaling factor
        lora_dropout=0.1,
        target_modules=["q", "v"],     # attention layers
        bias="none",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # ── Prepare data ──
    raw_data = load_and_prepare_data()

    # Train/validation split (90/10)
    split_idx = int(len(raw_data) * 0.9)
    train_data = raw_data[:split_idx]
    val_data = raw_data[split_idx:]

    train_dataset = Dataset.from_list(train_data)
    val_dataset = Dataset.from_list(val_data)

    # Tokenize
    train_dataset = train_dataset.map(
        lambda x: tokenize_data(x, tokenizer),
        batched=True,
        remove_columns=train_dataset.column_names,
    )
    val_dataset = val_dataset.map(
        lambda x: tokenize_data(x, tokenizer),
        batched=True,
        remove_columns=val_dataset.column_names,
    )

    print(f"  Train samples: {len(train_dataset)}")
    print(f"  Val samples:   {len(val_dataset)}")

    # ── Training arguments ──
    training_args = Seq2SeqTrainingArguments(
        output_dir=str(OUTPUT_DIR / "checkpoints"),
        num_train_epochs=5,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        learning_rate=2e-4,
        weight_decay=0.01,
        eval_strategy="epoch",
        save_strategy="epoch",
        logging_steps=20,
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        fp16=torch.cuda.is_available(),
        report_to="none",
    )

    data_collator = DataCollatorForSeq2Seq(
        tokenizer=tokenizer,
        model=model,
    )

    # ── Trainer ──
    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        data_collator=data_collator,
        tokenizer=tokenizer,
    )

    # ── Train ──
    print("\n🚀 Starting training...")
    train_result = trainer.train()

    print(f"\n  Training loss: {train_result.training_loss:.4f}")

    # ── Evaluate ──
    print("Evaluating...")
    eval_result = trainer.evaluate()
    print(f"  Eval loss: {eval_result['eval_loss']:.4f}")

    # ── Save model ──
    final_dir = OUTPUT_DIR / "final"
    final_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nSaving model to {final_dir}...")
    trainer.save_model(str(final_dir))
    tokenizer.save_pretrained(str(final_dir))

    # Save training metrics
    metrics = {
        "training_loss": train_result.training_loss,
        "eval_loss": eval_result["eval_loss"],
        "num_train_samples": len(train_dataset),
        "num_epochs": training_args.num_train_epochs,
        "base_model": BASE_MODEL,
    }
    with open(final_dir / "training_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    # ── Test generation ──
    print("\n🧪 Testing generation...")
    test_inputs = [
        "Generate an interview question for: Skills: Python, Django, PostgreSQL",
        "Generate an interview question for: Job Title: Data Scientist",
        "Generate an interview question for: Skills: React, TypeScript, Node.js",
    ]

    for test_input in test_inputs:
        inputs = tokenizer(test_input, return_tensors="pt", max_length=256, truncation=True)
        outputs = model.generate(
            **inputs,
            max_length=128,
            num_beams=3,
            do_sample=True,
            temperature=0.8,
        )
        generated = tokenizer.decode(outputs[0], skip_special_tokens=True)
        print(f"  Input:  {test_input}")
        print(f"  Output: {generated}")
        print()

    print("✅ Question generator training complete!")
    print(f"   Model saved to: {final_dir}")
    return metrics


if __name__ == "__main__":
    train()
