"""
EfficientNet-B0 Forgery Detection Training Script

Trains a binary classifier (authentic vs forged) using transfer learning
on EfficientNet-B0. Designed for small datasets with synthetic forgeries.

Usage:
    cd backend
    python training/train_forgery_cnn.py
"""

import os
import sys
import time

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, models, transforms


# ─── Configuration ────────────────────────────────────────────────

DATASET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset")
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml_models")
MODEL_PATH = os.path.join(MODEL_DIR, "efficientnet_forgery.pth")

BATCH_SIZE = 16
EPOCHS = 25
LEARNING_RATE = 1e-4
TRAIN_SPLIT = 0.8
IMG_SIZE = 224
NUM_CLASSES = 2  # authentic, forged


# ─── Device Selection ─────────────────────────────────────────────


def get_device():
    if torch.backends.mps.is_available():
        print("Using Apple Silicon GPU (MPS)")
        return torch.device("mps")
    elif torch.cuda.is_available():
        print("Using CUDA GPU")
        return torch.device("cuda")
    else:
        print("Using CPU")
        return torch.device("cpu")


# ─── Data Loading ─────────────────────────────────────────────────


def get_data_loaders():
    """Create train and validation data loaders."""
    train_transform = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(5),
        transforms.ColorJitter(brightness=0.2, contrast=0.2),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    val_transform = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    # Load full dataset to split
    full_dataset = datasets.ImageFolder(DATASET_DIR, transform=train_transform)
    print(f"Classes: {full_dataset.classes}")
    print(f"Class to idx: {full_dataset.class_to_idx}")
    print(f"Total images: {len(full_dataset)}")

    # Split into train/val
    train_size = int(TRAIN_SPLIT * len(full_dataset))
    val_size = len(full_dataset) - train_size
    train_dataset, val_dataset = random_split(full_dataset, [train_size, val_size])

    # Override transform for validation set
    val_dataset.dataset.transform = val_transform

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    print(f"Train: {len(train_dataset)}, Validation: {len(val_dataset)}")

    return train_loader, val_loader, full_dataset.class_to_idx


# ─── Model ────────────────────────────────────────────────────────


def create_model(device):
    """Create EfficientNet-B0 with modified classifier for binary classification."""
    model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)

    # Freeze early layers, fine-tune later layers
    for param in model.features[:6].parameters():
        param.requires_grad = False

    # Replace classifier
    model.classifier[1] = nn.Linear(1280, NUM_CLASSES)

    model = model.to(device)
    return model


# ─── Training Loop ────────────────────────────────────────────────


def train_one_epoch(model, loader, criterion, optimizer, device):
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0

    for images, labels in loader:
        images, labels = images.to(device), labels.to(device)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        running_loss += loss.item() * images.size(0)
        _, predicted = outputs.max(1)
        total += labels.size(0)
        correct += predicted.eq(labels).sum().item()

    epoch_loss = running_loss / total
    epoch_acc = 100.0 * correct / total
    return epoch_loss, epoch_acc


def validate(model, loader, criterion, device):
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0

    with torch.no_grad():
        for images, labels in loader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            loss = criterion(outputs, labels)

            running_loss += loss.item() * images.size(0)
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()

    epoch_loss = running_loss / total
    epoch_acc = 100.0 * correct / total
    return epoch_loss, epoch_acc


# ─── Main ─────────────────────────────────────────────────────────


def main():
    print("=" * 60)
    print("EfficientNet-B0 Forgery Detection Training")
    print("=" * 60)

    device = get_device()

    # Check dataset
    if not os.path.exists(DATASET_DIR):
        print(f"\nDataset not found at {DATASET_DIR}")
        print("Run generate_synthetic_data.py first!")
        sys.exit(1)

    # Data
    train_loader, val_loader, class_to_idx = get_data_loaders()

    # Model
    model = create_model(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=LEARNING_RATE,
    )
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=3, factor=0.5)

    # Training
    best_val_acc = 0.0
    os.makedirs(MODEL_DIR, exist_ok=True)

    print(f"\nTraining for {EPOCHS} epochs...\n")
    start_time = time.time()

    for epoch in range(EPOCHS):
        train_loss, train_acc = train_one_epoch(model, train_loader, criterion, optimizer, device)
        val_loss, val_acc = validate(model, val_loader, criterion, device)
        scheduler.step(val_loss)

        current_lr = optimizer.param_groups[0]["lr"]

        print(
            f"Epoch {epoch+1:2d}/{EPOCHS} | "
            f"Train Loss: {train_loss:.4f}, Acc: {train_acc:.1f}% | "
            f"Val Loss: {val_loss:.4f}, Acc: {val_acc:.1f}% | "
            f"LR: {current_lr:.6f}"
        )

        # Save best model
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), MODEL_PATH)
            print(f"  -> Saved best model (val acc: {val_acc:.1f}%)")

    elapsed = time.time() - start_time
    print(f"\nTraining complete in {elapsed:.0f}s")
    print(f"Best validation accuracy: {best_val_acc:.1f}%")
    print(f"Model saved to: {MODEL_PATH}")


if __name__ == "__main__":
    main()
