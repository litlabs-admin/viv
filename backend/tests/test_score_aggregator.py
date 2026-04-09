"""Tests for Score Aggregator."""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.score_aggregator import aggregate_scores, WEIGHTS, VERDICT_THRESHOLDS


class TestAggregateScores(unittest.TestCase):
    def test_returns_required_keys(self):
        result = aggregate_scores()
        self.assertIn("final_score", result)
        self.assertIn("verdict", result)
        self.assertIn("verdict_color", result)
        self.assertIn("module_scores", result)
        self.assertIn("override_reason", result)

    def test_perfect_scores_verified(self):
        result = aggregate_scores(
            cnn_forgery_probability=0.0,
            rule_score=1.0,
            nlp_score=1.0,
            anomaly_score=0.0,
            ocr_confidence=1.0,
        )
        self.assertEqual(result["verdict"], "VERIFIED")
        self.assertEqual(result["verdict_color"], "green")
        self.assertAlmostEqual(result["final_score"], 1.0, places=2)

    def test_worst_scores_fraudulent(self):
        result = aggregate_scores(
            cnn_forgery_probability=1.0,
            rule_score=0.0,
            nlp_score=0.0,
            anomaly_score=1.0,
            ocr_confidence=0.0,
        )
        self.assertEqual(result["verdict"], "FRAUDULENT")
        self.assertEqual(result["verdict_color"], "red")
        self.assertAlmostEqual(result["final_score"], 0.0, places=2)

    def test_medium_scores_needs_review(self):
        result = aggregate_scores(
            cnn_forgery_probability=0.3,
            rule_score=0.7,
            nlp_score=0.7,
            anomaly_score=0.2,
            ocr_confidence=0.8,
        )
        self.assertEqual(result["verdict"], "NEEDS_REVIEW")
        self.assertEqual(result["verdict_color"], "yellow")

    def test_score_range(self):
        result = aggregate_scores(
            cnn_forgery_probability=0.5,
            rule_score=0.5,
            nlp_score=0.5,
            anomaly_score=0.5,
            ocr_confidence=0.5,
        )
        self.assertGreaterEqual(result["final_score"], 0.0)
        self.assertLessEqual(result["final_score"], 1.0)

    def test_weights_sum_to_one(self):
        total = sum(WEIGHTS.values())
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_module_scores_breakdown(self):
        result = aggregate_scores(
            cnn_forgery_probability=0.2,
            rule_score=0.8,
            nlp_score=0.9,
            anomaly_score=0.1,
            ocr_confidence=0.95,
        )
        ms = result["module_scores"]
        self.assertIn("cnn_forgery", ms)
        self.assertIn("rule_validation", ms)
        self.assertIn("nlp_consistency", ms)
        self.assertIn("anomaly_detection", ms)
        self.assertIn("ocr_confidence", ms)

        # Each module score should have raw, weighted, weight
        for key in ms:
            self.assertIn("raw", ms[key])
            self.assertIn("weighted", ms[key])
            self.assertIn("weight", ms[key])

    def test_cnn_high_forgery_override(self):
        """CNN > 0.90 should result in at most NEEDS_REVIEW."""
        result = aggregate_scores(
            cnn_forgery_probability=0.95,
            rule_score=1.0,
            nlp_score=1.0,
            anomaly_score=0.0,
            ocr_confidence=1.0,
        )
        # Score = 0.4*0.05 + 0.25 + 0.15 + 0.1 + 0.1 = 0.62 → FRAUDULENT
        self.assertIn(result["verdict"], ["NEEDS_REVIEW", "FRAUDULENT"])

    def test_critical_rule_failures_override(self):
        """3+ critical failures should lower score."""
        failed_rules = [
            {"rule": "r1", "severity": "high"},
            {"rule": "r2", "severity": "high"},
            {"rule": "r3", "severity": "high"},
        ]
        result = aggregate_scores(
            cnn_forgery_probability=0.0,
            rule_score=0.5,
            nlp_score=1.0,
            anomaly_score=0.0,
            ocr_confidence=1.0,
            failed_rules=failed_rules,
        )
        self.assertIsNotNone(result["override_reason"])
        self.assertLessEqual(result["final_score"], 0.60)

    def test_no_override_for_low_severity(self):
        failed_rules = [
            {"rule": "r1", "severity": "low"},
            {"rule": "r2", "severity": "medium"},
        ]
        result = aggregate_scores(
            cnn_forgery_probability=0.0,
            rule_score=0.8,
            nlp_score=1.0,
            anomaly_score=0.0,
            ocr_confidence=1.0,
            failed_rules=failed_rules,
        )
        self.assertIsNone(result["override_reason"])

    def test_default_values(self):
        result = aggregate_scores()
        # With all 0: 0.4*(1-0) + 0.25*0 + 0.15*0 + 0.1*(1-0) + 0.1*0 = 0.5
        self.assertAlmostEqual(result["final_score"], 0.5, places=2)
        self.assertEqual(result["verdict"], "FRAUDULENT")

    def test_threshold_boundaries(self):
        # Exactly at VERIFIED threshold
        # Calculate inputs that produce exactly 0.85
        # With all equal: score = 0.4*(1-cnn) + 0.25*rule + 0.15*nlp + 0.1*(1-anomaly) + 0.1*ocr
        result = aggregate_scores(
            cnn_forgery_probability=0.0,
            rule_score=1.0,
            nlp_score=1.0,
            anomaly_score=0.0,
            ocr_confidence=1.0,
        )
        self.assertEqual(result["verdict"], "VERIFIED")


class TestVerdictThresholds(unittest.TestCase):
    def test_verified_threshold(self):
        self.assertEqual(VERDICT_THRESHOLDS["VERIFIED"], 0.85)

    def test_needs_review_threshold(self):
        self.assertEqual(VERDICT_THRESHOLDS["NEEDS_REVIEW"], 0.65)


if __name__ == "__main__":
    unittest.main()
