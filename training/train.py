"""
Training Engine for SHADOW-NET Deepfake Voice Detectors.
Trains CNNBaseline or adapted ResNet-18 on audio spectrograms.
Calculates and logs:
- Accuracy, Precision, Recall, F1
- ROC-AUC, Confusion Matrix, and False Positive Rate (FPR) per epoch.
Saves the best model checkpoint to model/resnet18.pth.
"""

import os
import sys
import time
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, Tuple

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
)

# Set up paths
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
_BACKEND_DIR = _PROJECT_ROOT / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from training.dataset import AudioSpoofDataset
from training.models import get_model

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("shadow_net.training")


def compute_epoch_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_probs: np.ndarray) -> Dict[str, Any]:
    """
    Computes classification evaluation metrics:
    - Accuracy, Precision, Recall, F1
    - ROC-AUC
    - Confusion Matrix & False Positive Rate (FPR)
    """
    acc = float(accuracy_score(y_true, y_pred))
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))

    try:
        auc = float(roc_auc_score(y_true, y_probs))
    except Exception:
        auc = 0.5  # In case only one class is present in batch/split

    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)
    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0

    return {
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "roc_auc": round(auc, 4),
        "fpr": round(fpr, 4),
        "confusion_matrix": {
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp),
        },
    }


def train_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
) -> Tuple[float, Dict[str, Any]]:
    """Runs a single training epoch."""
    model.train()
    total_loss = 0.0
    all_targets = []
    all_preds = []
    all_probs = []

    for inputs, targets in loader:
        inputs = inputs.to(device)
        targets = targets.to(device)

        optimizer.zero_grad()
        logits = model(inputs)
        loss = criterion(logits, targets)
        loss.backward()
        optimizer.step()

        total_loss += loss.item() * inputs.size(0)
        probs = torch.softmax(logits, dim=-1)[:, 1].detach().cpu().numpy()
        preds = torch.argmax(logits, dim=-1).detach().cpu().numpy()

        all_targets.extend(targets.cpu().numpy())
        all_preds.extend(preds)
        all_probs.extend(probs)

    avg_loss = total_loss / len(loader.dataset) if len(loader.dataset) > 0 else 0.0
    metrics = compute_epoch_metrics(np.array(all_targets), np.array(all_preds), np.array(all_probs))
    return avg_loss, metrics


def evaluate(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> Tuple[float, Dict[str, Any]]:
    """Evaluates the model on validation or test dataset."""
    model.eval()
    total_loss = 0.0
    all_targets = []
    all_preds = []
    all_probs = []

    with torch.no_grad():
        for inputs, targets in loader:
            inputs = inputs.to(device)
            targets = targets.to(device)

            logits = model(inputs)
            loss = criterion(logits, targets)

            total_loss += loss.item() * inputs.size(0)
            probs = torch.softmax(logits, dim=-1)[:, 1].cpu().numpy()
            preds = torch.argmax(logits, dim=-1).cpu().numpy()

            all_targets.extend(targets.cpu().numpy())
            all_preds.extend(preds)
            all_probs.extend(probs)

    avg_loss = total_loss / len(loader.dataset) if len(loader.dataset) > 0 else 0.0
    metrics = compute_epoch_metrics(np.array(all_targets), np.array(all_preds), np.array(all_probs))
    return avg_loss, metrics


def train_pipeline(
    model_name: str = "resnet18",
    data_dir: str = "data/synthetic",
    epochs: int = 5,
    batch_size: int = 16,
    lr: float = 1e-4,
    pretrained: bool = False,
    output_model: str = "model/resnet18.pth",
    device_name: str = None,
) -> Dict[str, Any]:
    """
    Main training pipeline.
    """
    data_path = Path(data_dir)
    train_manifest = data_path / "train.json"
    val_manifest = data_path / "val.json"

    if not train_manifest.is_file():
        raise FileNotFoundError(f"Training manifest not found: {train_manifest}. Run dataset_prep.py first.")
    if not val_manifest.is_file():
        raise FileNotFoundError(f"Validation manifest not found: {val_manifest}. Run dataset_prep.py first.")

    # Determine device
    if device_name:
        device = torch.device(device_name)
    else:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    logger.info(f"Using device: {device} | Model: {model_name} | Epochs: {epochs} | Batch Size: {batch_size}")

    # Build Datasets and DataLoaders
    train_ds = AudioSpoofDataset(str(train_manifest))
    val_ds = AudioSpoofDataset(str(val_manifest))

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, drop_last=False)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, drop_last=False)

    logger.info(f"Loaded datasets: {len(train_ds)} train samples, {len(val_ds)} validation samples")

    # Build Model
    model = get_model(model_name, pretrained=pretrained)
    model.to(device)

    # Loss & Optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)

    best_epoch = 0
    best_val_auc = -1.0
    best_val_loss = float("inf")
    best_metrics = {}

    out_path = Path(output_model)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 80)
    print(f"SHADOW-NET Training Pipeline: {model_name.upper()} on {len(train_ds)} samples")
    print("=" * 80)

    for epoch in range(1, epochs + 1):
        t0 = time.time()
        train_loss, train_metrics = train_epoch(model, train_loader, criterion, optimizer, device)
        val_loss, val_metrics = evaluate(model, val_loader, criterion, device)
        scheduler.step()
        elapsed = time.time() - t0

        print(
            f"Epoch [{epoch:02d}/{epochs:02d}] ({elapsed:.1f}s) | "
            f"Train Loss: {train_loss:.4f}, Acc: {train_metrics['accuracy']:.3f}, F1: {train_metrics['f1']:.3f} | "
            f"Val Loss: {val_loss:.4f}, Acc: {val_metrics['accuracy']:.3f}, F1: {val_metrics['f1']:.3f}, "
            f"AUC: {val_metrics['roc_auc']:.3f}, FPR: {val_metrics['fpr']:.3f}"
        )

        # Save best model checkpoint
        is_best = val_metrics["roc_auc"] > best_val_auc or (
            val_metrics["roc_auc"] == best_val_auc and val_loss < best_val_loss
        )
        if is_best:
            best_epoch = epoch
            best_val_auc = val_metrics["roc_auc"]
            best_val_loss = val_loss
            best_metrics = val_metrics

            checkpoint = {
                "state_dict": model.state_dict(),
                "epoch": epoch,
                "model_name": model_name,
                "metrics": val_metrics,
            }
            torch.save(checkpoint, str(out_path))
            logger.info(f"Saved checkpoint to {out_path} (Val AUC: {best_val_auc:.4f})")

    last_path = out_path.with_name(out_path.stem + ".last" + out_path.suffix)
    torch.save({"state_dict": model.state_dict(), "epoch": epoch, "model_name": model_name,
                "metrics": val_metrics}, str(last_path))
    print("=" * 80)
    print(f"Training Complete. Best Checkpoint saved at: {out_path}")
    print(f"Final Validation Metrics: Acc={best_metrics.get('accuracy', 0):.4f}, "
          f"F1={best_metrics.get('f1', 0):.4f}, ROC-AUC={best_metrics.get('roc_auc', 0):.4f}, "
          f"FPR={best_metrics.get('fpr', 0):.4f}")
    print("=" * 80 + "\n")

    return {
        "output_path": str(out_path),
        "best_epoch": best_epoch,
        "metrics": best_metrics,
    }


def main():
    parser = argparse.ArgumentParser(description="Train SHADOW-NET Audio Deepfake Classifier")
    parser.add_argument("--model", type=str, default="resnet18", choices=["resnet18", "cnn"], help="Model architecture")
    parser.add_argument("--data-dir", type=str, default="data/synthetic", help="Directory with train.json, val.json")
    parser.add_argument("--epochs", type=int, default=5, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=16, help="Mini-batch size")
    parser.add_argument("--lr", type=float, default=1e-4, help="Learning rate")
    parser.add_argument("--pretrained", action="store_true", help="Use pretrained torchvision weights")
    parser.add_argument("--output-model", type=str, default="model/resnet18.pth", help="Output .pth file path")
    parser.add_argument("--device", type=str, default=None, help="Device (cpu, cuda)")

    args = parser.parse_args()
    train_pipeline(
        model_name=args.model,
        data_dir=args.data_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        pretrained=args.pretrained,
        output_model=args.output_model,
        device_name=args.device,
    )


if __name__ == "__main__":
    main()
