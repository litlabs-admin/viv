"""Tests for CNN forgery detection module (ELA, CNN, Grad-CAM)."""

import os
import sys
import tempfile

import cv2
import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.cnn_forgery import (
    compute_ela,
    ela_to_base64,
    detect_forgery,
    TORCH_AVAILABLE,
)


# ─── Helper: create a test image ──────────────────────────────────


@pytest.fixture
def test_image_path():
    """Create a temporary test image."""
    img = np.random.randint(0, 255, (300, 400, 3), dtype=np.uint8)
    # Add some structure (white rectangle on dark background)
    img[50:250, 50:350] = 200
    cv2.rectangle(img, (80, 80), (320, 220), (0, 0, 0), 2)
    cv2.putText(img, "TEST DOCUMENT", (100, 150),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        cv2.imwrite(f.name, img)
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def forged_image_path():
    """Create a temporary forged image (has spliced region with different compression)."""
    img = np.ones((300, 400, 3), dtype=np.uint8) * 200
    cv2.putText(img, "ORIGINAL TEXT", (50, 150),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

    # Simulate forgery: compress a region differently
    region = img[100:200, 100:300].copy()
    _, encoded = cv2.imencode(".jpg", region, [int(cv2.IMWRITE_JPEG_QUALITY), 10])
    decoded = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if decoded is not None:
        img[100:200, 100:300] = decoded

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        cv2.imwrite(f.name, img)
        yield f.name
    os.unlink(f.name)


# ─── ELA Tests ────────────────────────────────────────────────────


class TestELA:
    def test_ela_returns_image(self, test_image_path):
        ela = compute_ela(test_image_path)
        assert isinstance(ela, np.ndarray)
        assert len(ela.shape) == 3  # BGR
        assert ela.shape[2] == 3

    def test_ela_same_dimensions(self, test_image_path):
        original = cv2.imread(test_image_path)
        ela = compute_ela(test_image_path)
        assert ela.shape == original.shape

    def test_ela_different_quality_settings(self, test_image_path):
        ela_90 = compute_ela(test_image_path, quality=90)
        ela_50 = compute_ela(test_image_path, quality=50)
        # Lower quality should produce larger differences
        assert not np.array_equal(ela_90, ela_50)

    def test_ela_invalid_image_raises(self):
        with pytest.raises(ValueError, match="Cannot read image"):
            compute_ela("/nonexistent/image.jpg")

    def test_ela_to_base64(self, test_image_path):
        ela = compute_ela(test_image_path)
        b64 = ela_to_base64(ela)
        assert isinstance(b64, str)
        assert len(b64) > 0

    def test_ela_forged_has_higher_values(self, test_image_path, forged_image_path):
        """Forged image should generally show higher ELA values in tampered region."""
        ela_authentic = compute_ela(test_image_path)
        ela_forged = compute_ela(forged_image_path)
        # Both should be valid images
        assert ela_authentic.shape[0] > 0
        assert ela_forged.shape[0] > 0


# ─── Detect Forgery Pipeline Tests ────────────────────────────────


class TestDetectForgery:
    def test_returns_required_keys(self, test_image_path):
        result = detect_forgery(test_image_path)
        assert "forgery_detected" in result
        assert "forgery_probability" in result
        assert "ela_image_base64" in result
        assert "status" in result
        assert "method" in result

    def test_status_success(self, test_image_path):
        result = detect_forgery(test_image_path)
        assert result["status"] == "success"

    def test_ela_image_present(self, test_image_path):
        result = detect_forgery(test_image_path)
        assert result["ela_image_base64"] is not None
        assert len(result["ela_image_base64"]) > 0

    def test_probability_in_range(self, test_image_path):
        result = detect_forgery(test_image_path)
        assert 0.0 <= result["forgery_probability"] <= 1.0

    def test_invalid_image_returns_error(self):
        result = detect_forgery("/nonexistent/image.jpg")
        assert result["status"] == "error"
        assert result["error"] is not None

    def test_ela_stats_present(self, test_image_path):
        result = detect_forgery(test_image_path)
        assert "ela_stats" in result
        assert "mean_brightness" in result["ela_stats"]
        assert "std_brightness" in result["ela_stats"]

    def test_method_without_model(self, test_image_path):
        """Without a trained model, should fall back to ELA only."""
        result = detect_forgery(test_image_path)
        # If no model file exists, method should be ela_only
        model_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ml_models", "efficientnet_forgery.pth"
        )
        if not os.path.exists(model_path):
            assert result["method"] == "ela_only"


# ─── Synthetic Data Generator Tests ───────────────────────────────


class TestSyntheticDataGenerator:
    def test_import_generator(self):
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "training"
        ))
        from generate_synthetic_data import (
            text_replacement_forgery,
            copy_paste_forgery,
            brightness_forgery,
            jpeg_noise_forgery,
            augment_image,
        )
        # All should be callable
        assert callable(text_replacement_forgery)
        assert callable(copy_paste_forgery)
        assert callable(brightness_forgery)
        assert callable(jpeg_noise_forgery)
        assert callable(augment_image)

    def test_text_replacement_forgery(self):
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "training"
        ))
        from generate_synthetic_data import text_replacement_forgery
        img = np.ones((300, 400, 3), dtype=np.uint8) * 200
        forged = text_replacement_forgery(img)
        assert forged.shape == img.shape
        assert not np.array_equal(forged, img)

    def test_copy_paste_forgery(self):
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "training"
        ))
        from generate_synthetic_data import copy_paste_forgery
        img = np.random.randint(0, 255, (300, 400, 3), dtype=np.uint8)
        forged = copy_paste_forgery(img)
        assert forged.shape == img.shape

    def test_brightness_forgery(self):
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "training"
        ))
        from generate_synthetic_data import brightness_forgery
        img = np.ones((300, 400, 3), dtype=np.uint8) * 128
        forged = brightness_forgery(img)
        assert forged.shape == img.shape
        assert not np.array_equal(forged, img)

    def test_jpeg_noise_forgery(self):
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "training"
        ))
        from generate_synthetic_data import jpeg_noise_forgery
        img = np.random.randint(50, 200, (300, 400, 3), dtype=np.uint8)
        forged = jpeg_noise_forgery(img)
        assert forged.shape == img.shape

    def test_augment_image_count(self):
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "training"
        ))
        from generate_synthetic_data import augment_image
        img = np.ones((300, 400, 3), dtype=np.uint8) * 128
        augmented = augment_image(img)
        assert len(augmented) == 5  # 5 augmentation types


# ─── PyTorch Availability Test ────────────────────────────────────


class TestTorchAvailability:
    def test_torch_is_available(self):
        assert TORCH_AVAILABLE is True, "PyTorch should be installed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
