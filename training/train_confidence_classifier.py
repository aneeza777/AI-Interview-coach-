"""
Train Confidence Classifier
=============================
Trains a neural network classifier on audio features to predict
speaking confidence level.

Features (extracted by librosa):
  [WPM, pitch_cv, pause_ratio, volume_cv, pauses_per_min]

Labels:
  0 = nervous
  1 = moderate
  2 = confident

After training, saved to models_output/confidence_classifier/
"""

import os
import json
import numpy as np
from pathlib import Path

# ML
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, accuracy_score


# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
DATA_PATH = Path(__file__).parent / "data" / "confidence_classification_dataset.json"
OUTPUT_DIR = Path(__file__).parent / "models_output" / "confidence_classifier"


# ──────────────────────────────────────────────
# Neural Network Model
# ──────────────────────────────────────────────
class ConfidenceNet(nn.Module):
    """Simple feedforward network for confidence classification."""

    def __init__(self, input_dim=5, hidden_dim=64, num_classes=3):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Linear(32, num_classes),
        )

    def forward(self, x):
        return self.network(x)


def load_data():
    """Load and split dataset."""
    with open(DATA_PATH, "r") as f:
        data = json.load(f)

    features = np.array([d["features"] for d in data], dtype=np.float32)
    labels = np.array([d["label"] for d in data], dtype=np.int64)

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        features, labels, test_size=0.2, random_state=42, stratify=labels
    )

    # Normalize features
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    return X_train, X_test, y_train, y_test, scaler


def train():
    """Main training loop."""
    print("=" * 60)
    print("  Training Confidence Classifier (PyTorch)")
    print("=" * 60)

    # ── Load data ──
    X_train, X_test, y_train, y_test, scaler = load_data()
    print(f"\n  Train samples: {len(X_train)}")
    print(f"  Test samples:  {len(X_test)}")

    # ── Convert to PyTorch tensors ──
    X_train_t = torch.FloatTensor(X_train)
    y_train_t = torch.LongTensor(y_train)
    X_test_t = torch.FloatTensor(X_test)
    y_test_t = torch.LongTensor(y_test)

    train_dataset = TensorDataset(X_train_t, y_train_t)
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)

    # ── Model ──
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"  Device: {device}")

    model = ConfidenceNet(input_dim=5).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=20, gamma=0.5)

    # ── Training loop ──
    num_epochs = 80
    best_acc = 0.0

    print(f"\n🚀 Training for {num_epochs} epochs...")

    for epoch in range(num_epochs):
        model.train()
        total_loss = 0
        correct = 0
        total = 0

        for batch_X, batch_y in train_loader:
            batch_X, batch_y = batch_X.to(device), batch_y.to(device)

            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            total += batch_y.size(0)
            correct += (predicted == batch_y).sum().item()

        scheduler.step()

        # Evaluate every 10 epochs
        if (epoch + 1) % 10 == 0:
            train_acc = 100 * correct / total

            model.eval()
            with torch.no_grad():
                test_outputs = model(X_test_t.to(device))
                _, test_predicted = torch.max(test_outputs.data, 1)
                test_acc = 100 * (test_predicted == y_test_t.to(device)).sum().item() / len(y_test)

            print(f"  Epoch {epoch+1:3d}/{num_epochs} | Loss: {total_loss/len(train_loader):.4f} | "
                  f"Train Acc: {train_acc:.1f}% | Test Acc: {test_acc:.1f}%")

            if test_acc > best_acc:
                best_acc = test_acc

    # ── Final evaluation ──
    model.eval()
    with torch.no_grad():
        test_outputs = model(X_test_t.to(device))
        _, test_predicted = torch.max(test_outputs.data, 1)

    y_pred = test_predicted.cpu().numpy()
    print(f"\n📊 Classification Report:")
    print(classification_report(y_test, y_pred, target_names=["nervous", "moderate", "confident"]))

    # ── Save model and scaler ──
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    model_path = OUTPUT_DIR / "confidence_net.pth"
    torch.save({
        "model_state_dict": model.state_dict(),
        "scaler_mean": scaler.mean_.tolist(),
        "scaler_scale": scaler.scale_.tolist(),
        "input_dim": 5,
        "num_classes": 3,
    }, str(model_path))

    # Save scaler params
    scaler_path = OUTPUT_DIR / "scaler_params.json"
    with open(scaler_path, "w") as f:
        json.dump({
            "mean": scaler.mean_.tolist(),
            "scale": scaler.scale_.tolist(),
        }, f, indent=2)

    # Save metrics
    metrics = {
        "best_test_accuracy": best_acc,
        "final_test_accuracy": accuracy_score(y_test, y_pred),
        "num_epochs": num_epochs,
        "input_features": ["wpm", "pitch_cv", "pause_ratio", "volume_cv", "pauses_per_min"],
        "classes": ["nervous", "moderate", "confident"],
    }
    with open(OUTPUT_DIR / "training_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"\n✅ Confidence classifier training complete!")
    print(f"   Model saved to: {model_path}")
    print(f"   Best test accuracy: {best_acc:.1f}%")
    return metrics


if __name__ == "__main__":
    train()
