"""Tests for Isolation Forest Anomaly Detector."""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.anomaly_detector import (
    detect_anomaly,
    extract_marksheet_features,
    extract_generic_features,
    heuristic_anomaly_score,
)


class TestExtractMarksheetFeatures(unittest.TestCase):
    def test_valid_subjects(self):
        fields = {
            "sgpa": 7.5,
            "subjects": [
                {"total_marks": 100, "internal_marks": 30, "external_marks": 70},
                {"total_marks": 90, "internal_marks": 25, "external_marks": 65},
                {"total_marks": 110, "internal_marks": 35, "external_marks": 75},
            ],
        }
        features = extract_marksheet_features(fields)
        self.assertIsNotNone(features)
        self.assertEqual(len(features), 7)
        self.assertAlmostEqual(features[0], 7.5)  # SGPA

    def test_no_subjects(self):
        fields = {"sgpa": 7.5}
        features = extract_marksheet_features(fields)
        self.assertIsNone(features)

    def test_empty_subjects(self):
        fields = {"sgpa": 7.5, "subjects": []}
        features = extract_marksheet_features(fields)
        self.assertIsNone(features)

    def test_no_sgpa(self):
        fields = {
            "subjects": [
                {"total_marks": 100, "internal_marks": 30, "external_marks": 70},
            ],
        }
        features = extract_marksheet_features(fields)
        self.assertIsNotNone(features)
        self.assertEqual(features[0], 0.0)  # default SGPA

    def test_feature_order(self):
        fields = {
            "sgpa": 8.0,
            "subjects": [
                {"total_marks": 120, "internal_marks": 40, "external_marks": 80},
                {"total_marks": 80, "internal_marks": 20, "external_marks": 60},
            ],
        }
        features = extract_marksheet_features(fields)
        self.assertEqual(features[0], 8.0)   # SGPA
        self.assertEqual(features[1], 100.0)  # Mean marks
        self.assertEqual(features[3], 2.0)    # Num subjects
        self.assertEqual(features[5], 120.0)  # Max marks
        self.assertEqual(features[6], 80.0)   # Min marks


class TestExtractGenericFeatures(unittest.TestCase):
    def test_basic(self):
        fields = {"name": "Vivek", "dob": "01/01/2000", "age": 24}
        features = extract_generic_features(fields)
        self.assertEqual(len(features), 4)
        self.assertEqual(features[0], 3.0)  # 3 non-null fields
        self.assertEqual(features[2], 1.0)  # 1 numeric field (age)

    def test_empty_fields(self):
        features = extract_generic_features({})
        self.assertEqual(len(features), 4)
        self.assertEqual(features[0], 0.0)

    def test_none_values(self):
        fields = {"name": None, "dob": None}
        features = extract_generic_features(fields)
        self.assertEqual(features[0], 0.0)  # no non-null


class TestHeuristicAnomalyScore(unittest.TestCase):
    def test_normal_marksheet(self):
        features = [7.5, 95.0, 12.0, 6.0, 0.5, 120.0, 70.0]
        score = heuristic_anomaly_score(features, "sppu_marksheet")
        self.assertLess(score, 0.5)

    def test_perfect_marks_suspicious(self):
        features = [10.0, 150.0, 0.0, 6.0, 0.5, 150.0, 150.0]
        score = heuristic_anomaly_score(features, "sppu_marksheet")
        self.assertGreater(score, 0.2)

    def test_impossible_sgpa(self):
        features = [15.0, 50.0, 5.0, 6.0, 0.5, 55.0, 45.0]
        score = heuristic_anomaly_score(features, "sppu_marksheet")
        self.assertGreater(score, 0.2)

    def test_all_same_marks(self):
        features = [7.0, 100.0, 0.5, 6.0, 0.5, 100.5, 99.5]
        score = heuristic_anomaly_score(features, "sppu_marksheet")
        self.assertGreater(score, 0.1)  # std < 1 triggers flag

    def test_generic_type(self):
        features = [3.0, 50.0, 1.0, 10.0]
        score = heuristic_anomaly_score(features, "aadhaar_card")
        self.assertEqual(score, 0.1)

    def test_score_capped_at_1(self):
        features = [15.0, 200.0, 60.0, 1.0, 5.0, 200.0, 200.0]
        score = heuristic_anomaly_score(features, "sppu_marksheet")
        self.assertLessEqual(score, 1.0)


class TestDetectAnomaly(unittest.TestCase):
    def test_returns_required_keys(self):
        fields = {
            "sgpa": 7.5,
            "subjects": [
                {"total_marks": 100, "internal_marks": 30, "external_marks": 70},
            ],
        }
        result = detect_anomaly(fields, "sppu_marksheet")
        self.assertIn("anomaly_score", result)
        self.assertIn("is_anomaly", result)
        self.assertIn("method", result)
        self.assertIn("status", result)

    def test_success_status(self):
        fields = {
            "sgpa": 7.5,
            "subjects": [
                {"total_marks": 100, "internal_marks": 30, "external_marks": 70},
            ],
        }
        result = detect_anomaly(fields, "sppu_marksheet")
        self.assertEqual(result["status"], "success")

    def test_score_range(self):
        fields = {
            "sgpa": 8.0,
            "subjects": [
                {"total_marks": 100, "internal_marks": 30, "external_marks": 70},
                {"total_marks": 90, "internal_marks": 25, "external_marks": 65},
            ],
        }
        result = detect_anomaly(fields, "sppu_marksheet")
        self.assertGreaterEqual(result["anomaly_score"], 0.0)
        self.assertLessEqual(result["anomaly_score"], 1.0)

    def test_none_fields(self):
        result = detect_anomaly(None, "sppu_marksheet")
        self.assertEqual(result["status"], "skipped")

    def test_empty_fields(self):
        result = detect_anomaly({}, "sppu_marksheet")
        self.assertEqual(result["status"], "skipped")

    def test_generic_doc_type(self):
        fields = {"name": "Vivek", "pan_number": "ABCDE1234F"}
        result = detect_anomaly(fields, "pan_card")
        self.assertEqual(result["status"], "success")

    def test_has_features(self):
        fields = {
            "sgpa": 7.5,
            "subjects": [
                {"total_marks": 100, "internal_marks": 30, "external_marks": 70},
            ],
        }
        result = detect_anomaly(fields, "sppu_marksheet")
        self.assertIsNotNone(result["features"])

    def test_uses_trained_model_if_available(self):
        """If isolation_forest.pkl exists, method should be 'isolation_forest'."""
        fields = {
            "sgpa": 7.5,
            "subjects": [
                {"total_marks": 100, "internal_marks": 30, "external_marks": 70},
                {"total_marks": 90, "internal_marks": 25, "external_marks": 65},
                {"total_marks": 110, "internal_marks": 35, "external_marks": 75},
            ],
        }
        result = detect_anomaly(fields, "sppu_marksheet")
        model_exists = os.path.exists(
            os.path.join(os.path.dirname(__file__), "..", "ml_models", "isolation_forest.pkl")
        )
        if model_exists:
            self.assertEqual(result["method"], "isolation_forest")
        else:
            self.assertEqual(result["method"], "heuristic")


if __name__ == "__main__":
    unittest.main()
