"""
CNN Forgery Detection Module

Combines:
1. Error Level Analysis (ELA) — visual indicator of tampering
2. EfficientNet-B0 CNN — trained classifier (authentic vs forged)
3. Grad-CAM — heatmap showing where model detects tampering

Returns structured forgery detection results.
"""

import os
import io
import base64

import cv2
import numpy as np
from PIL import Image

# PyTorch imports — optional, gracefully handle if not installed
try:
    import torch
    import torch.nn.functional as F
    from torchvision import models, transforms
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from config import BASE_DIR


# Model path
MODEL_PATH = os.path.join(BASE_DIR, "ml_models", "efficientnet_forgery.pth")


# ─── Error Level Analysis (ELA) ───────────────────────────────────


def compute_ela(image_path: str, quality: int = 90, scale: int = 15) -> np.ndarray:
    """
    Compute Error Level Analysis image.

    Re-saves image at a known JPEG quality, then computes the pixel-wise
    difference. Tampered regions typically show brighter in the ELA image
    because they have different compression artifacts.

    Args:
        image_path: Path to the input image
        quality: JPEG quality for re-compression (default 90)
        scale: Amplification factor for differences (default 15)

    Returns:
        ELA image as numpy array (BGR)
    """
    original = cv2.imread(image_path)
    if original is None:
        raise ValueError(f"Cannot read image: {image_path}")

    # Re-save at specified quality
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    _, encoded = cv2.imencode(".jpg", original, encode_param)
    resaved = cv2.imdecode(encoded, cv2.IMREAD_COLOR)

    # Compute difference and amplify
    diff = cv2.absdiff(original, resaved)
    ela = np.clip(diff * scale, 0, 255).astype(np.uint8)

    return ela


def ela_to_base64(ela_image: np.ndarray) -> str:
    """Convert ELA numpy array to base64 string for API response."""
    _, buffer = cv2.imencode(".png", ela_image)
    return base64.b64encode(buffer).decode("utf-8")


# ─── CNN Model Loading ────────────────────────────────────────────


def _get_device():
    """Get the best available device."""
    if not TORCH_AVAILABLE:
        return None
    if torch.backends.mps.is_available():
        return torch.device("mps")
    elif torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def load_model():
    """
    Load the trained EfficientNet-B0 forgery detection model.
    Returns (model, device) or (None, None) if not available.
    """
    if not TORCH_AVAILABLE:
        return None, None

    if not os.path.exists(MODEL_PATH):
        return None, None

    device = _get_device()
    model = models.efficientnet_b0(weights=None)
    model.classifier[1] = torch.nn.Linear(1280, 2)

    state_dict = torch.load(MODEL_PATH, map_location=device, weights_only=True)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()

    return model, device


# Image transform (same as used during training)
TRANSFORM = None
if TORCH_AVAILABLE:
    TRANSFORM = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])


def preprocess_for_cnn(image_path: str):
    """Load and preprocess image for CNN inference."""
    if not TORCH_AVAILABLE or TRANSFORM is None:
        return None
    img = Image.open(image_path).convert("RGB")
    return TRANSFORM(img).unsqueeze(0)


# ─── Grad-CAM Visualization ───────────────────────────────────────


class GradCAM:
    """Grad-CAM implementation for EfficientNet-B0."""

    def __init__(self, model, target_layer):
        self.model = model
        self.target_layer = target_layer
        self.gradients = None
        self.activations = None

        # Register hooks
        target_layer.register_forward_hook(self._forward_hook)
        target_layer.register_full_backward_hook(self._backward_hook)

    def _forward_hook(self, module, input, output):
        self.activations = output.detach()

    def _backward_hook(self, module, grad_input, grad_output):
        self.gradients = grad_output[0].detach()

    def generate(self, input_tensor, target_class=None):
        """Generate Grad-CAM heatmap."""
        self.model.eval()
        output = self.model(input_tensor)

        if target_class is None:
            target_class = output.argmax(dim=1).item()

        self.model.zero_grad()
        output[0, target_class].backward()

        # Pool gradients across spatial dimensions
        weights = self.gradients.mean(dim=[2, 3], keepdim=True)

        # Weighted combination of activation maps
        cam = (weights * self.activations).sum(dim=1, keepdim=True)
        cam = F.relu(cam)

        # Normalize to [0, 1]
        cam = cam.squeeze().cpu().numpy()
        if cam.max() > 0:
            cam = cam / cam.max()

        return cam


def generate_gradcam_heatmap(
    model, device, image_path: str, original_image: np.ndarray
) -> np.ndarray:
    """
    Generate Grad-CAM heatmap overlay on the original image.

    Returns:
        Heatmap overlay image as numpy array (BGR)
    """
    if model is None or not TORCH_AVAILABLE:
        return None

    # Get last conv layer of EfficientNet-B0
    target_layer = model.features[-1]
    grad_cam = GradCAM(model, target_layer)

    # Preprocess
    input_tensor = preprocess_for_cnn(image_path)
    if input_tensor is None:
        return None
    input_tensor = input_tensor.to(device)
    input_tensor.requires_grad_(True)

    # Generate CAM
    cam = grad_cam.generate(input_tensor, target_class=1)  # class 1 = forged

    # Resize to original image size
    h, w = original_image.shape[:2]
    cam_resized = cv2.resize(cam, (w, h))

    # Create heatmap
    heatmap = cv2.applyColorMap(np.uint8(255 * cam_resized), cv2.COLORMAP_JET)

    # Overlay on original
    overlay = cv2.addWeighted(original_image, 0.6, heatmap, 0.4, 0)

    return overlay


def heatmap_to_base64(heatmap: np.ndarray) -> str:
    """Convert heatmap numpy array to base64 string."""
    if heatmap is None:
        return None
    _, buffer = cv2.imencode(".png", heatmap)
    return base64.b64encode(buffer).decode("utf-8")


# ─── Main Forgery Detection Pipeline ──────────────────────────────


def detect_forgery(image_path: str) -> dict:
    """
    Run the full forgery detection pipeline on a document image.

    Pipeline:
    1. Compute ELA image
    2. Run CNN inference (if model available)
    3. Generate Grad-CAM heatmap (if model available)

    Args:
        image_path: Path to the document image

    Returns:
        Dict with forgery detection results
    """
    result = {
        "forgery_detected": False,
        "forgery_probability": 0.0,
        "ela_image_base64": None,
        "gradcam_heatmap_base64": None,
        "method": "ela_only",
        "status": "success",
        "error": None,
    }

    try:
        # Step 1: ELA
        ela_image = compute_ela(image_path)
        result["ela_image_base64"] = ela_to_base64(ela_image)

        # ELA-based heuristic score (mean brightness of ELA indicates tampering)
        ela_gray = cv2.cvtColor(ela_image, cv2.COLOR_BGR2GRAY)
        ela_mean = float(np.mean(ela_gray))
        ela_std = float(np.std(ela_gray))

        # Higher mean/std in ELA suggests more compression inconsistencies
        ela_score = min(ela_mean / 30.0, 1.0)  # Normalize to 0-1

        # Step 2: CNN inference
        model, device = load_model()

        if model is not None:
            result["method"] = "cnn+ela"

            input_tensor = preprocess_for_cnn(image_path)
            if input_tensor is not None:
                input_tensor = input_tensor.to(device)

                with torch.no_grad():
                    output = model(input_tensor)
                    probabilities = F.softmax(output, dim=1)
                    forge_prob = probabilities[0][1].item()

                result["forgery_probability"] = round(forge_prob, 4)
                result["forgery_detected"] = forge_prob > 0.5

                # Step 3: Grad-CAM (only if forgery suspected)
                if forge_prob > 0.3:
                    original = cv2.imread(image_path)
                    heatmap = generate_gradcam_heatmap(model, device, image_path, original)
                    result["gradcam_heatmap_base64"] = heatmap_to_base64(heatmap)

                    # Save heatmap to outputs directory
                    output_dir = os.path.join(BASE_DIR, "outputs")
                    os.makedirs(output_dir, exist_ok=True)
                    base_name = os.path.splitext(os.path.basename(image_path))[0]
                    if heatmap is not None:
                        cv2.imwrite(
                            os.path.join(output_dir, f"{base_name}_gradcam.png"),
                            heatmap,
                        )
        else:
            # No CNN model — use ELA heuristic only
            result["method"] = "ela_only"
            result["forgery_probability"] = round(ela_score, 4)
            result["forgery_detected"] = ela_score > 0.5

        # Add ELA stats for debugging
        result["ela_stats"] = {
            "mean_brightness": round(ela_mean, 2),
            "std_brightness": round(ela_std, 2),
        }

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result
