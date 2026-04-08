"""Tests for the preprocessing module."""

import cv2
import numpy as np
import os
import sys
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.preprocessor import (
    resize_if_needed,
    deskew,
    enhance_image,
    binarize,
    sharpen,
    preprocess_document,
)


def create_test_image(width=800, height=1000, color=True):
    """Create a synthetic test document image."""
    if color:
        img = np.ones((height, width, 3), dtype=np.uint8) * 240  # light gray background
        # Add some "text" lines
        for y in range(100, 800, 40):
            cv2.line(img, (50, y), (width - 50, y), (30, 30, 30), 2)
        # Add a "header"
        cv2.rectangle(img, (50, 30), (width - 50, 80), (0, 0, 150), -1)
    else:
        img = np.ones((height, width), dtype=np.uint8) * 240
        for y in range(100, 800, 40):
            cv2.line(img, (50, y), (width - 50, y), 30, 2)
    return img


class TestResizeIfNeeded:
    def test_no_resize_needed(self):
        img = create_test_image(800, 1000)
        result = resize_if_needed(img)
        assert result.shape == img.shape

    def test_resize_large_image(self):
        img = create_test_image(5000, 6000)
        result = resize_if_needed(img)
        assert max(result.shape[:2]) <= 4000

    def test_maintains_aspect_ratio(self):
        img = create_test_image(6000, 3000)
        result = resize_if_needed(img)
        original_ratio = 6000 / 3000
        new_ratio = result.shape[1] / result.shape[0]
        assert abs(original_ratio - new_ratio) < 0.01


class TestDeskew:
    def test_straight_image_unchanged(self):
        img = create_test_image()
        result = deskew(img)
        # Straight image should remain roughly the same size
        assert abs(result.shape[0] - img.shape[0]) <= 2
        assert abs(result.shape[1] - img.shape[1]) <= 2

    def test_returns_image(self):
        img = create_test_image()
        result = deskew(img)
        assert isinstance(result, np.ndarray)
        assert len(result.shape) == 3


class TestEnhanceImage:
    def test_output_same_shape(self):
        img = create_test_image()
        result = enhance_image(img)
        assert result.shape == img.shape

    def test_output_is_uint8(self):
        img = create_test_image()
        result = enhance_image(img)
        assert result.dtype == np.uint8


class TestBinarize:
    def test_output_is_2d(self):
        img = create_test_image()
        result = binarize(img)
        assert len(result.shape) == 2  # grayscale

    def test_output_is_binary(self):
        img = create_test_image()
        result = binarize(img)
        unique_vals = np.unique(result)
        assert all(v in [0, 255] for v in unique_vals)

    def test_grayscale_input(self):
        img = create_test_image(color=False)
        result = binarize(img)
        assert len(result.shape) == 2


class TestSharpen:
    def test_output_same_shape(self):
        img = create_test_image()
        result = sharpen(img)
        assert result.shape == img.shape


class TestPreprocessDocument:
    def test_full_pipeline(self, tmp_path):
        # Create and save a test image
        img = create_test_image()
        test_file = str(tmp_path / "test_doc.jpg")
        cv2.imwrite(test_file, img)

        result = preprocess_document(test_file)

        assert "original" in result
        assert "corrected" in result
        assert "enhanced" in result
        assert "binary" in result
        assert "sharpened" in result

        # All should be numpy arrays
        for key, val in result.items():
            assert isinstance(val, np.ndarray), f"{key} is not ndarray"

    def test_invalid_file_raises(self):
        with pytest.raises(ValueError):
            preprocess_document("/nonexistent/file.jpg")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
