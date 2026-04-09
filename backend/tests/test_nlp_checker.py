"""Tests for NLP Semantic Consistency Checker."""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.nlp_checker import (
    check_nlp_consistency,
    check_name_consistency,
    check_date_consistency,
    check_institution_validity,
    check_field_completeness,
    _normalize_name,
    _parse_date,
)


class TestNormalizeName(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(_normalize_name("John Doe"), "JOHN DOE")

    def test_extra_spaces(self):
        self.assertEqual(_normalize_name("  John   Doe  "), "JOHN DOE")

    def test_empty(self):
        self.assertEqual(_normalize_name(""), "")

    def test_none(self):
        self.assertEqual(_normalize_name(None), "")


class TestParseDate(unittest.TestCase):
    def test_dd_mm_yyyy_slash(self):
        d = _parse_date("15/06/2000")
        self.assertIsNotNone(d)
        self.assertEqual(d.day, 15)
        self.assertEqual(d.month, 6)

    def test_dd_mm_yyyy_dash(self):
        d = _parse_date("15-06-2000")
        self.assertIsNotNone(d)

    def test_yyyy_mm_dd(self):
        d = _parse_date("2000-06-15")
        self.assertIsNotNone(d)

    def test_invalid(self):
        self.assertIsNone(_parse_date("not-a-date"))

    def test_empty(self):
        self.assertIsNone(_parse_date(""))


class TestNameConsistency(unittest.TestCase):
    def test_valid_name(self):
        fields = {"name": "Vivek Kumar", "father_name": "Rajesh Kumar"}
        findings = check_name_consistency(fields)
        self.assertEqual(len(findings), 0)

    def test_single_name(self):
        fields = {"name": "Vivek"}
        findings = check_name_consistency(fields)
        self.assertTrue(any("one part" in f for f in findings))

    def test_father_same_as_candidate(self):
        fields = {"name": "Vivek Kumar", "father_name": "Vivek Kumar"}
        findings = check_name_consistency(fields)
        self.assertTrue(any("identical" in f for f in findings))

    def test_no_name(self):
        fields = {"dob": "01/01/2000"}
        findings = check_name_consistency(fields)
        self.assertTrue(any("No primary name" in f for f in findings))

    def test_student_name(self):
        fields = {"student_name": "Vivek Kumar"}
        findings = check_name_consistency(fields)
        self.assertEqual(len(findings), 0)

    def test_employee_name(self):
        fields = {"employee_name": "Vivek Kumar"}
        findings = check_name_consistency(fields)
        self.assertEqual(len(findings), 0)


class TestDateConsistency(unittest.TestCase):
    def test_aadhaar_valid(self):
        fields = {"dob": "15/06/2000"}
        findings = check_date_consistency(fields, "aadhaar_card")
        self.assertEqual(len(findings), 0)

    def test_aadhaar_future_dob(self):
        fields = {"dob": "15/06/2050"}
        findings = check_date_consistency(fields, "aadhaar_card")
        self.assertTrue(any("future" in f.lower() for f in findings))

    def test_aadhaar_too_old(self):
        fields = {"dob": "15/06/1800"}
        findings = check_date_consistency(fields, "aadhaar_card")
        self.assertTrue(any("impossibly" in f.lower() for f in findings))

    def test_experience_young_at_joining(self):
        fields = {
            "dob": "15/06/2010",
            "date_of_joining": "01/01/2020",
            "date_of_relieving": "01/01/2022",
        }
        findings = check_date_consistency(fields, "experience_certificate")
        self.assertTrue(any("minimum working age" in f for f in findings))

    def test_experience_long_tenure(self):
        fields = {
            "date_of_joining": "01/01/1960",
            "date_of_relieving": "01/01/2020",
        }
        findings = check_date_consistency(fields, "experience_certificate")
        self.assertTrue(any("unusually long" in f for f in findings))

    def test_pan_underage(self):
        fields = {"dob": "15/06/2020"}
        findings = check_date_consistency(fields, "pan_card")
        self.assertTrue(any("only" in f.lower() for f in findings))

    def test_marksheet_no_dates(self):
        fields = {}
        findings = check_date_consistency(fields, "sppu_marksheet")
        self.assertEqual(len(findings), 0)


class TestInstitutionValidity(unittest.TestCase):
    def test_known_college(self):
        fields = {"college_name": "Pune Institute of Computer Technology"}
        findings = check_institution_validity(fields)
        self.assertEqual(len(findings), 0)

    def test_known_abbreviation(self):
        fields = {"college_name": "PICT"}
        findings = check_institution_validity(fields)
        self.assertEqual(len(findings), 0)

    def test_unknown_college(self):
        fields = {"college_name": "Totally Fake University of Nowhere"}
        findings = check_institution_validity(fields)
        self.assertTrue(len(findings) > 0)

    def test_no_college(self):
        fields = {"name": "Test Student"}
        findings = check_institution_validity(fields)
        self.assertEqual(len(findings), 0)

    def test_empty_college(self):
        fields = {"college_name": ""}
        findings = check_institution_validity(fields)
        self.assertEqual(len(findings), 0)


class TestFieldCompleteness(unittest.TestCase):
    def test_marksheet_complete(self):
        fields = {
            "student_name": "Vivek",
            "prn": "12345678901",
            "semester": 5,
            "subjects": [{"name": "Math"}],
            "sgpa": 8.0,
        }
        findings = check_field_completeness(fields, "sppu_marksheet")
        self.assertEqual(len(findings), 0)

    def test_marksheet_missing_fields(self):
        fields = {"student_name": "Vivek"}
        findings = check_field_completeness(fields, "sppu_marksheet")
        self.assertTrue(any("Missing" in f for f in findings))

    def test_aadhaar_complete(self):
        fields = {"aadhaar_number": "123456789012", "name": "Vivek", "dob": "01/01/2000"}
        findings = check_field_completeness(fields, "aadhaar_card")
        self.assertEqual(len(findings), 0)

    def test_unknown_doc_type(self):
        fields = {"name": "Test"}
        findings = check_field_completeness(fields, "unknown")
        self.assertEqual(len(findings), 0)


class TestCheckNlpConsistency(unittest.TestCase):
    def test_returns_required_keys(self):
        fields = {"name": "Vivek Kumar", "dob": "15/06/2000"}
        result = check_nlp_consistency(fields, "aadhaar_card")
        self.assertIn("score", result)
        self.assertIn("findings", result)
        self.assertIn("status", result)

    def test_success_status(self):
        fields = {
            "aadhaar_number": "123456789012",
            "name": "Vivek Kumar",
            "dob": "15/06/2000",
        }
        result = check_nlp_consistency(fields, "aadhaar_card")
        self.assertEqual(result["status"], "success")

    def test_score_range(self):
        fields = {"name": "Vivek Kumar"}
        result = check_nlp_consistency(fields, "pan_card")
        self.assertGreaterEqual(result["score"], 0.0)
        self.assertLessEqual(result["score"], 1.0)

    def test_none_fields(self):
        result = check_nlp_consistency(None, "aadhaar_card")
        self.assertEqual(result["status"], "skipped")

    def test_empty_fields(self):
        result = check_nlp_consistency({}, "aadhaar_card")
        self.assertEqual(result["status"], "skipped")

    def test_perfect_marksheet(self):
        fields = {
            "student_name": "Vivek Kumar",
            "prn": "12345678901",
            "semester": 5,
            "subjects": [{"name": "Math"}],
            "sgpa": 8.0,
            "college_name": "Pune Institute of Computer Technology",
        }
        result = check_nlp_consistency(fields, "sppu_marksheet")
        self.assertEqual(result["status"], "success")
        self.assertGreater(result["score"], 0.5)

    def test_findings_list(self):
        fields = {"name": "X"}  # Single-part name + missing fields
        result = check_nlp_consistency(fields, "pan_card")
        self.assertIsInstance(result["findings"], list)


if __name__ == "__main__":
    unittest.main()
