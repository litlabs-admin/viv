"""Tests for Report Generator."""

import unittest
import sys
import os
import tempfile

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.report_generator import (
    generate_summary_text,
    generate_annotated_image,
    generate_report,
)


class TestGenerateSummaryText(unittest.TestCase):
    def test_verified_summary(self):
        summary = generate_summary_text(
            verdict="VERIFIED",
            final_score=0.92,
            doc_type="sppu_marksheet",
            failed_rules=[],
            nlp_findings=[],
            forgery_detected=False,
            forgery_probability=0.05,
            is_anomaly=False,
        )
        self.assertIn("verified", summary.lower())
        self.assertIn("92%", summary)

    def test_fraudulent_summary(self):
        summary = generate_summary_text(
            verdict="FRAUDULENT",
            final_score=0.30,
            doc_type="aadhaar_card",
            failed_rules=[{"rule": "checksum", "severity": "high", "description": "Verhoeff failed"}],
            nlp_findings=["Name mismatch"],
            forgery_detected=True,
            forgery_probability=0.85,
            is_anomaly=True,
        )
        self.assertIn("fraudulent", summary.lower())
        self.assertIn("CNN", summary)

    def test_needs_review_summary(self):
        summary = generate_summary_text(
            verdict="NEEDS_REVIEW",
            final_score=0.72,
            doc_type="pan_card",
            failed_rules=[],
            nlp_findings=["Minor inconsistency"],
            forgery_detected=False,
            forgery_probability=0.1,
            is_anomaly=False,
        )
        self.assertIn("review", summary.lower())

    def test_doc_type_display_name(self):
        summary = generate_summary_text(
            verdict="VERIFIED", final_score=0.9, doc_type="sppu_marksheet",
            failed_rules=[], nlp_findings=[], forgery_detected=False,
            forgery_probability=0.0, is_anomaly=False,
        )
        self.assertIn("SPPU Marksheet", summary)

    def test_unknown_doc_type(self):
        summary = generate_summary_text(
            verdict="VERIFIED", final_score=0.9, doc_type="unknown_type",
            failed_rules=[], nlp_findings=[], forgery_detected=False,
            forgery_probability=0.0, is_anomaly=False,
        )
        self.assertIn("Document", summary)

    def test_anomaly_mentioned(self):
        summary = generate_summary_text(
            verdict="NEEDS_REVIEW", final_score=0.7, doc_type="sppu_marksheet",
            failed_rules=[], nlp_findings=[], forgery_detected=False,
            forgery_probability=0.1, is_anomaly=True,
        )
        self.assertIn("anomaly", summary.lower())

    def test_multiple_findings(self):
        summary = generate_summary_text(
            verdict="FRAUDULENT", final_score=0.3, doc_type="sppu_marksheet",
            failed_rules=[
                {"rule": "r1", "severity": "high", "description": "SGPA mismatch"},
                {"rule": "r2", "severity": "high", "description": "Grade wrong"},
            ],
            nlp_findings=["Name issue", "Date issue"],
            forgery_detected=True,
            forgery_probability=0.9,
            is_anomaly=True,
        )
        self.assertIn("SGPA mismatch", summary)


class TestGenerateAnnotatedImage(unittest.TestCase):
    def setUp(self):
        # Create a temp image
        self.temp_dir = tempfile.mkdtemp()
        self.img_path = os.path.join(self.temp_dir, "test_doc.jpg")
        img = np.ones((200, 300, 3), dtype=np.uint8) * 255
        cv2.imwrite(self.img_path, img)

    def test_creates_annotated_image(self):
        output = generate_annotated_image(self.img_path, False, "VERIFIED", "test123")
        self.assertIsNotNone(output)
        self.assertTrue(os.path.exists(output))

    def test_invalid_image_returns_none(self):
        output = generate_annotated_image("/nonexistent/path.jpg", False, "VERIFIED", "test123")
        self.assertIsNone(output)

    def test_different_verdicts(self):
        for verdict in ["VERIFIED", "NEEDS_REVIEW", "FRAUDULENT"]:
            output = generate_annotated_image(self.img_path, False, verdict, f"test_{verdict}")
            self.assertIsNotNone(output)


class TestGenerateReport(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.img_path = os.path.join(self.temp_dir, "test_doc.jpg")
        img = np.ones((200, 300, 3), dtype=np.uint8) * 255
        cv2.imwrite(self.img_path, img)

    def test_returns_required_keys(self):
        result = generate_report(
            document_id="test123",
            doc_type="sppu_marksheet",
            image_path=self.img_path,
            preprocessing_result={"status": "success"},
            classification_result={"confidence": 0.9, "method": "keyword"},
            ocr_result={"status": "success", "extracted_fields": {"name": "Test"}},
            rule_result={"status": "success", "score": 0.9, "passed": [], "failed": []},
            nlp_result={"status": "success", "score": 0.8, "findings": []},
            forgery_result={"status": "success", "forgery_detected": False, "forgery_probability": 0.1, "method": "ela_only"},
            anomaly_result={"status": "success", "anomaly_score": 0.1, "is_anomaly": False, "method": "heuristic"},
            aggregation_result={"final_score": 0.9, "verdict": "VERIFIED", "verdict_color": "green", "module_scores": {}, "override_reason": None},
        )
        self.assertIn("summary", result)
        self.assertIn("full_report", result)
        self.assertIn("verdict", result)
        self.assertIn("final_score", result)

    def test_full_report_structure(self):
        result = generate_report(
            document_id="test123",
            doc_type="aadhaar_card",
            image_path=self.img_path,
            preprocessing_result={"status": "success"},
            classification_result={"confidence": 0.9, "method": "keyword"},
            ocr_result={"status": "success", "extracted_fields": {"name": "Test"}},
            rule_result={"status": "success", "score": 0.8, "passed": [], "failed": []},
            nlp_result={"status": "success", "score": 0.7, "findings": []},
            forgery_result={"status": "success", "forgery_detected": False, "forgery_probability": 0.1, "method": "cnn+ela"},
            anomaly_result={"status": "success", "anomaly_score": 0.1, "is_anomaly": False, "method": "isolation_forest"},
            aggregation_result={"final_score": 0.85, "verdict": "VERIFIED", "verdict_color": "green", "module_scores": {}, "override_reason": None},
        )
        report = result["full_report"]
        self.assertEqual(report["document_id"], "test123")
        self.assertEqual(report["doc_type"], "aadhaar_card")
        self.assertIn("timestamp", report)
        self.assertIn("rule_validation", report)
        self.assertIn("nlp_consistency", report)
        self.assertIn("cnn_forgery", report)
        self.assertIn("anomaly_detection", report)

    def test_no_image_path(self):
        result = generate_report(
            document_id="test123",
            doc_type="pan_card",
            image_path=None,
            preprocessing_result={"status": "success"},
            classification_result={"confidence": 0.9, "method": "keyword"},
            ocr_result={"status": "success", "extracted_fields": {}},
            rule_result={"status": "success", "score": 0.5, "passed": [], "failed": []},
            nlp_result={"status": "success", "score": 0.5, "findings": []},
            forgery_result={"status": "success", "forgery_detected": False, "forgery_probability": 0.0, "method": "ela_only"},
            anomaly_result={"status": "success", "anomaly_score": 0.0, "is_anomaly": False, "method": "heuristic"},
            aggregation_result={"final_score": 0.7, "verdict": "NEEDS_REVIEW", "verdict_color": "yellow", "module_scores": {}, "override_reason": None},
        )
        self.assertIsNone(result["annotated_image_path"])


if __name__ == "__main__":
    unittest.main()
