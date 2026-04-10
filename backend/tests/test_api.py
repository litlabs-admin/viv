"""Tests for the FastAPI endpoints."""

import os
import sys
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from database import init_db

# Ensure tables exist before tests run
init_db()

client = TestClient(app)


def create_test_image_bytes():
    """Create a test image and return as JPEG bytes."""
    img = np.ones((500, 400, 3), dtype=np.uint8) * 200
    cv2.rectangle(img, (20, 20), (380, 60), (0, 0, 100), -1)
    for y in range(100, 400, 30):
        cv2.line(img, (30, y), (370, y), (40, 40, 40), 1)
    _, buffer = cv2.imencode(".jpg", img)
    return buffer.tobytes()


class TestRootEndpoint:
    def test_root(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Document Verification System"
        assert data["status"] == "running"

    def test_health(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestUploadEndpoint:
    def test_upload_success(self):
        image_bytes = create_test_image_bytes()
        response = client.post(
            "/api/upload",
            files={"file": ("test_document.jpg", image_bytes, "image/jpeg")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "document_id" in data
        assert data["filename"] == "test_document.jpg"
        assert data["status"] == "uploaded"
        assert "file_hash" in data

    def test_upload_invalid_extension(self):
        response = client.post(
            "/api/upload",
            files={"file": ("test.txt", b"hello", "text/plain")},
        )
        assert response.status_code == 400
        assert "not supported" in response.json()["detail"]

    def test_upload_png(self):
        img = np.ones((100, 100, 3), dtype=np.uint8) * 128
        _, buffer = cv2.imencode(".png", img)
        response = client.post(
            "/api/upload",
            files={"file": ("doc.png", buffer.tobytes(), "image/png")},
        )
        assert response.status_code == 200


class TestVerifyEndpoint:
    def test_verify_uploaded_doc(self):
        # First upload
        image_bytes = create_test_image_bytes()
        upload_resp = client.post(
            "/api/upload",
            files={"file": ("verify_test.jpg", image_bytes, "image/jpeg")},
        )
        doc_id = upload_resp.json()["document_id"]

        # Then verify
        verify_resp = client.post(f"/api/verify/{doc_id}")
        assert verify_resp.status_code == 200
        data = verify_resp.json()
        assert data["status"] == "completed"
        assert data["preprocessing"]["status"] == "success"
        assert "image_shape" in data["preprocessing"]
        assert "verdict" in data
        assert "final_score" in data

    def test_verify_nonexistent_doc(self):
        response = client.post("/api/verify/nonexistent-id")
        assert response.status_code == 404


class TestResultsEndpoint:
    def test_get_results_uploaded_doc(self):
        # Upload a document
        image_bytes = create_test_image_bytes()
        upload_resp = client.post(
            "/api/upload",
            files={"file": ("results_test.jpg", image_bytes, "image/jpeg")},
        )
        doc_id = upload_resp.json()["document_id"]

        # Get results (no verification run yet)
        results_resp = client.get(f"/api/results/{doc_id}")
        assert results_resp.status_code == 200
        data = results_resp.json()
        assert data["document_id"] == doc_id
        assert data["status"] == "uploaded"

    def test_get_results_nonexistent(self):
        response = client.get("/api/results/nonexistent-id")
        assert response.status_code == 404


class TestHistoryEndpoint:
    def test_get_history(self):
        response = client.get("/api/history")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "documents" in data
        assert isinstance(data["documents"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
