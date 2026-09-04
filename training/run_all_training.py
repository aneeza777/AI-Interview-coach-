"""
Run All Training
=================
Master script that runs the complete training pipeline:
1. Prepare datasets
2. Train question generator (FLAN-T5 + LoRA)
3. Train answer evaluator (sentence-transformers)
4. Train confidence classifier (PyTorch NN)

Usage: py run_all_training.py
"""

import time
import json
from pathlib import Path


def main():
    print("\n" + "=" * 60)
    print("  🎯 AI Interview Coach — Full Training Pipeline")
    print("=" * 60)

    start_time = time.time()
    results = {}

    # ── Step 1: Prepare datasets ──
    print("\n" + "─" * 60)
    print("  STEP 1/4: Preparing Datasets")
    print("─" * 60)

    try:
        from prepare_datasets import (
            prepare_question_generation_dataset,
            prepare_answer_evaluation_dataset,
            prepare_confidence_dataset,
        )
        prepare_question_generation_dataset()
        prepare_answer_evaluation_dataset()
        prepare_confidence_dataset()
        results["datasets"] = "✅ Success"
    except Exception as e:
        print(f"❌ Dataset preparation failed: {e}")
        results["datasets"] = f"❌ Failed: {e}"
        return

    # ── Step 2: Train Question Generator ──
    print("\n" + "─" * 60)
    print("  STEP 2/4: Training Question Generator (FLAN-T5 + LoRA)")
    print("─" * 60)

    try:
        from train_question_generator import train as train_qg
        qg_metrics = train_qg()
        results["question_generator"] = f"✅ Loss: {qg_metrics.get('eval_loss', 'N/A'):.4f}"
    except Exception as e:
        print(f"❌ Question generator training failed: {e}")
        print("   (Continuing with other models...)")
        results["question_generator"] = f"❌ Failed: {e}"

    # ── Step 3: Train Answer Evaluator ──
    print("\n" + "─" * 60)
    print("  STEP 3/4: Training Answer Evaluator (sentence-transformers)")
    print("─" * 60)

    try:
        from train_answer_evaluator import train as train_ae
        ae_metrics = train_ae()
        results["answer_evaluator"] = "✅ Trained successfully"
    except Exception as e:
        print(f"❌ Answer evaluator training failed: {e}")
        print("   (Continuing with other models...)")
        results["answer_evaluator"] = f"❌ Failed: {e}"

    # ── Step 4: Train Confidence Classifier ──
    print("\n" + "─" * 60)
    print("  STEP 4/4: Training Confidence Classifier (PyTorch)")
    print("─" * 60)

    try:
        from train_confidence_classifier import train as train_cc
        cc_metrics = train_cc()
        results["confidence_classifier"] = f"✅ Accuracy: {cc_metrics.get('best_test_accuracy', 'N/A'):.1f}%"
    except Exception as e:
        print(f"❌ Confidence classifier training failed: {e}")
        results["confidence_classifier"] = f"❌ Failed: {e}"

    # ── Summary ──
    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)

    print("\n" + "=" * 60)
    print("  📊 Training Summary")
    print("=" * 60)
    print(f"  Time: {minutes}m {seconds}s")
    print()

    for name, status in results.items():
        print(f"  {name:.<35} {status}")

    # Save summary
    output_dir = Path(__file__).parent / "models_output"
    output_dir.mkdir(exist_ok=True)

    with open(output_dir / "training_summary.json", "w") as f:
        json.dump({
            "elapsed_seconds": elapsed,
            "results": results,
        }, f, indent=2)

    print("\n" + "=" * 60)
    all_ok = all("✅" in v for v in results.values())
    if all_ok:
        print("  ✅ All models trained successfully!")
        print("  Trained models saved to: training/models_output/")
        print("\n  The backend will automatically use these models.")
        print("  Run 'start.bat' to launch the website.")
    else:
        print("  ⚠️ Some models failed to train.")
        print("  The backend will fall back to default models.")
        print("  Check the errors above and retry failed steps.")
    print("=" * 60)


if __name__ == "__main__":
    main()
