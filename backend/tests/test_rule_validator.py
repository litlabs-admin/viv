"""Tests for rule-based document validator and Verhoeff algorithm."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.rule_validator import (
    verhoeff_checksum,
    validate_sppu_marksheet,
    validate_aadhaar_card,
    validate_pan_card,
    validate_experience_certificate,
    validate_document,
)


# ─── Verhoeff Algorithm Tests ──────────────────────────────────────


class TestVerhoeffChecksum:
    def test_valid_aadhaar_number(self):
        assert verhoeff_checksum("499118665246") is True

    def test_invalid_aadhaar_number(self):
        # Change last digit to invalidate checksum
        assert verhoeff_checksum("499118665247") is False

    def test_single_digit_change_detected(self):
        valid = "499118665246"
        # Change one digit in the middle
        invalid = "499118665236"
        assert verhoeff_checksum(valid) is True
        assert verhoeff_checksum(invalid) is False

    def test_empty_string(self):
        assert verhoeff_checksum("") is False

    def test_non_digit_string(self):
        assert verhoeff_checksum("abcdefghijkl") is False

    def test_mixed_string(self):
        assert verhoeff_checksum("1234abcd5678") is False

    def test_known_valid_number(self):
        # "2363" is a known valid Verhoeff number
        assert verhoeff_checksum("2363") is True

    def test_known_invalid_number(self):
        assert verhoeff_checksum("2364") is False


# ─── SPPU Marksheet Validation Tests ───────────────────────────────


class TestSPPUValidation:
    def _valid_fields(self):
        """Return a valid SPPU marksheet field set."""
        return {
            "prn": "12345678901",
            "student_name": "Test Student",
            "semester": 4,
            "subjects": [
                {
                    "subject_name": "Mathematics",
                    "credits": 4,
                    "internal_marks": 40,
                    "external_marks": 75,
                    "total_marks": 115,
                    "grade": "A",
                    "grade_points": 8,
                },
                {
                    "subject_name": "Physics",
                    "credits": 3,
                    "internal_marks": 40,
                    "external_marks": 60,
                    "total_marks": 100,
                    "grade": "B+",
                    "grade_points": 7,
                },
            ],
            "sgpa": 7.57,  # (4*8 + 3*7) / (4+3) = 53/7 = 7.571...
            "result": "PASS",
        }

    def test_valid_marksheet_all_pass(self):
        result = validate_sppu_marksheet(self._valid_fields())
        assert result["score"] >= 0.8
        assert len(result["failed"]) == 0

    def test_invalid_prn_too_short(self):
        fields = self._valid_fields()
        fields["prn"] = "12345"
        result = validate_sppu_marksheet(fields)
        prn_fails = [f for f in result["failed"] if f["rule"] == "prn_format"]
        assert len(prn_fails) == 1

    def test_missing_prn(self):
        fields = self._valid_fields()
        del fields["prn"]
        result = validate_sppu_marksheet(fields)
        prn_fails = [f for f in result["failed"] if f["rule"] == "prn_format"]
        assert len(prn_fails) == 1

    def test_invalid_semester(self):
        fields = self._valid_fields()
        fields["semester"] = 10
        result = validate_sppu_marksheet(fields)
        sem_fails = [f for f in result["failed"] if f["rule"] == "semester_range"]
        assert len(sem_fails) == 1

    def test_marks_total_mismatch(self):
        fields = self._valid_fields()
        fields["subjects"][0]["total_marks"] = 99  # Should be 80
        result = validate_sppu_marksheet(fields)
        marks_fails = [f for f in result["failed"] if f["rule"] == "marks_total"]
        assert len(marks_fails) >= 1

    def test_grade_inconsistency(self):
        fields = self._valid_fields()
        fields["subjects"][0]["grade"] = "O"  # 80/150 should be A, not O
        result = validate_sppu_marksheet(fields)
        grade_fails = [f for f in result["failed"] if f["rule"] == "grade_consistency"]
        assert len(grade_fails) >= 1

    def test_grade_points_mismatch(self):
        fields = self._valid_fields()
        fields["subjects"][0]["grade_points"] = 10  # Grade A should be 8, not 10
        result = validate_sppu_marksheet(fields)
        gp_fails = [f for f in result["failed"] if f["rule"] == "grade_points_match"]
        assert len(gp_fails) >= 1

    def test_sgpa_mismatch(self):
        fields = self._valid_fields()
        fields["sgpa"] = 9.5  # Actual computed ~7.57
        result = validate_sppu_marksheet(fields)
        sgpa_fails = [f for f in result["failed"] if f["rule"] == "sgpa_calculation"]
        assert len(sgpa_fails) == 1

    def test_result_pass_with_f_grade(self):
        fields = self._valid_fields()
        fields["subjects"][0]["grade"] = "F"
        result = validate_sppu_marksheet(fields)
        result_fails = [f for f in result["failed"] if f["rule"] == "result_consistency"]
        assert len(result_fails) == 1

    def test_result_fail_without_f_grade(self):
        fields = self._valid_fields()
        fields["result"] = "FAIL"
        result = validate_sppu_marksheet(fields)
        result_fails = [f for f in result["failed"] if f["rule"] == "result_consistency"]
        assert len(result_fails) == 1

    def test_empty_subjects(self):
        fields = self._valid_fields()
        fields["subjects"] = []
        result = validate_sppu_marksheet(fields)
        # Should still validate PRN and semester
        assert result["score"] >= 0


# ─── Aadhaar Card Validation Tests ─────────────────────────────────


class TestAadhaarValidation:
    def _valid_fields(self):
        return {
            "aadhaar_number": "499118665246",
            "name": "Rahul Kumar",
            "dob": "15/06/1995",
            "gender": "MALE",
        }

    def test_valid_aadhaar_all_pass(self):
        result = validate_aadhaar_card(self._valid_fields())
        assert result["score"] >= 0.8
        assert len(result["failed"]) == 0

    def test_invalid_aadhaar_format(self):
        fields = self._valid_fields()
        fields["aadhaar_number"] = "12345"
        result = validate_aadhaar_card(fields)
        fmt_fails = [f for f in result["failed"] if f["rule"] == "aadhaar_format"]
        assert len(fmt_fails) == 1

    def test_aadhaar_with_spaces(self):
        fields = self._valid_fields()
        fields["aadhaar_number"] = "4991 1866 5246"
        result = validate_aadhaar_card(fields)
        fmt_passes = [p for p in result["passed"] if p["rule"] == "aadhaar_format"]
        assert len(fmt_passes) == 1

    def test_verhoeff_fails_on_tampered(self):
        fields = self._valid_fields()
        fields["aadhaar_number"] = "499118665247"  # Invalid checksum
        result = validate_aadhaar_card(fields)
        verhoeff_fails = [f for f in result["failed"] if f["rule"] == "aadhaar_verhoeff"]
        assert len(verhoeff_fails) == 1

    def test_aadhaar_starts_with_zero(self):
        fields = self._valid_fields()
        fields["aadhaar_number"] = "036849758023"
        result = validate_aadhaar_card(fields)
        first_digit_fails = [f for f in result["failed"] if f["rule"] == "aadhaar_first_digit"]
        assert len(first_digit_fails) == 1

    def test_missing_aadhaar_number(self):
        fields = self._valid_fields()
        del fields["aadhaar_number"]
        result = validate_aadhaar_card(fields)
        assert len(result["failed"]) > 0

    def test_future_dob(self):
        fields = self._valid_fields()
        fields["dob"] = "15/06/2099"
        result = validate_aadhaar_card(fields)
        dob_fails = [f for f in result["failed"] if f["rule"] == "dob_future"]
        assert len(dob_fails) == 1

    def test_invalid_gender(self):
        fields = self._valid_fields()
        fields["gender"] = "INVALID"
        result = validate_aadhaar_card(fields)
        gender_fails = [f for f in result["failed"] if f["rule"] == "gender_valid"]
        assert len(gender_fails) == 1

    def test_valid_vid(self):
        fields = self._valid_fields()
        fields["vid"] = "1234567890123456"
        result = validate_aadhaar_card(fields)
        vid_passes = [p for p in result["passed"] if p["rule"] == "vid_format"]
        assert len(vid_passes) == 1

    def test_invalid_vid(self):
        fields = self._valid_fields()
        fields["vid"] = "12345"
        result = validate_aadhaar_card(fields)
        vid_fails = [f for f in result["failed"] if f["rule"] == "vid_format"]
        assert len(vid_fails) == 1


# ─── PAN Card Validation Tests ─────────────────────────────────────


class TestPANValidation:
    def _valid_fields(self):
        return {
            "pan_number": "ABCPD1234E",
            "name": "Amit Sharma",
            "fathers_name": "Raj Sharma",
            "dob": "10/03/1990",
        }

    def test_valid_pan_all_pass(self):
        result = validate_pan_card(self._valid_fields())
        assert result["score"] > 0.7
        assert all(f["severity"] != "high" for f in result["failed"])

    def test_invalid_pan_format(self):
        fields = self._valid_fields()
        fields["pan_number"] = "1234567890"
        result = validate_pan_card(fields)
        fmt_fails = [f for f in result["failed"] if f["rule"] == "pan_format"]
        assert len(fmt_fails) == 1

    def test_missing_pan(self):
        fields = self._valid_fields()
        del fields["pan_number"]
        result = validate_pan_card(fields)
        fmt_fails = [f for f in result["failed"] if f["rule"] == "pan_format"]
        assert len(fmt_fails) == 1

    def test_pan_entity_type_person(self):
        fields = self._valid_fields()
        fields["pan_number"] = "ABCPD1234E"  # 4th char P = Person
        result = validate_pan_card(fields)
        entity_passes = [p for p in result["passed"] if p["rule"] == "pan_entity_type"]
        assert len(entity_passes) == 1

    def test_pan_name_match(self):
        fields = self._valid_fields()
        fields["pan_number"] = "ABCPA1234E"  # 5th char A matches "Amit"
        fields["name"] = "Amit Sharma"
        result = validate_pan_card(fields)
        name_passes = [p for p in result["passed"] if p["rule"] == "pan_name_match"]
        assert len(name_passes) == 1

    def test_pan_name_mismatch(self):
        fields = self._valid_fields()
        fields["pan_number"] = "ABCPX1234E"  # 5th char X doesn't match "Amit"
        fields["name"] = "Amit Sharma"
        result = validate_pan_card(fields)
        name_fails = [f for f in result["failed"] if f["rule"] == "pan_name_match"]
        assert len(name_fails) == 1

    def test_future_dob(self):
        fields = self._valid_fields()
        fields["dob"] = "10/03/2099"
        result = validate_pan_card(fields)
        dob_fails = [f for f in result["failed"] if f["rule"] == "dob_valid"]
        assert len(dob_fails) == 1

    def test_missing_name(self):
        fields = self._valid_fields()
        del fields["name"]
        result = validate_pan_card(fields)
        name_fails = [f for f in result["failed"] if f["rule"] == "name_present"]
        assert len(name_fails) == 1


# ─── Experience Certificate Validation Tests ───────────────────────


class TestExperienceCertValidation:
    def _valid_fields(self):
        return {
            "employee_name": "Priya Patel",
            "company_name": "TCS",
            "designation": "Software Engineer",
            "date_of_joining": "01/06/2020",
            "date_of_relieving": "30/05/2023",
            "duration": "2 years 11 months",
        }

    def test_valid_certificate_all_pass(self):
        result = validate_experience_certificate(self._valid_fields())
        assert result["score"] > 0.8
        assert len(result["failed"]) == 0

    def test_relieving_before_joining(self):
        fields = self._valid_fields()
        fields["date_of_joining"] = "01/06/2023"
        fields["date_of_relieving"] = "01/01/2020"
        result = validate_experience_certificate(fields)
        date_fails = [f for f in result["failed"] if f["rule"] == "dates_order"]
        assert len(date_fails) == 1

    def test_duration_mismatch(self):
        fields = self._valid_fields()
        fields["duration"] = "5 years"  # Actual ~3 years
        result = validate_experience_certificate(fields)
        dur_fails = [f for f in result["failed"] if f["rule"] == "duration_consistency"]
        assert len(dur_fails) == 1

    def test_duration_matches(self):
        fields = self._valid_fields()
        fields["date_of_joining"] = "01/01/2020"
        fields["date_of_relieving"] = "01/01/2022"
        fields["duration"] = "2 years"
        result = validate_experience_certificate(fields)
        dur_passes = [p for p in result["passed"] if p["rule"] == "duration_consistency"]
        assert len(dur_passes) == 1

    def test_future_joining_date(self):
        fields = self._valid_fields()
        fields["date_of_joining"] = "01/06/2099"
        fields["date_of_relieving"] = "01/06/2100"
        result = validate_experience_certificate(fields)
        future_fails = [f for f in result["failed"] if f["rule"] == "joining_future"]
        assert len(future_fails) == 1

    def test_missing_employee_name(self):
        fields = self._valid_fields()
        del fields["employee_name"]
        result = validate_experience_certificate(fields)
        name_fails = [f for f in result["failed"] if f["rule"] == "employee_name_present"]
        assert len(name_fails) == 1

    def test_missing_company_name(self):
        fields = self._valid_fields()
        del fields["company_name"]
        result = validate_experience_certificate(fields)
        company_fails = [f for f in result["failed"] if f["rule"] == "company_name_present"]
        assert len(company_fails) == 1

    def test_missing_dates(self):
        fields = self._valid_fields()
        del fields["date_of_joining"]
        del fields["date_of_relieving"]
        result = validate_experience_certificate(fields)
        date_fails = [f for f in result["failed"] if f["rule"] == "date_missing"]
        assert len(date_fails) == 2

    def test_unparseable_date(self):
        fields = self._valid_fields()
        fields["date_of_joining"] = "not-a-date"
        fields["date_of_relieving"] = "also-not-a-date"
        result = validate_experience_certificate(fields)
        parse_fails = [f for f in result["failed"] if f["rule"] == "date_parse"]
        assert len(parse_fails) == 2


# ─── Main validate_document() Entry Point Tests ────────────────────


class TestValidateDocument:
    def test_valid_doc_type_runs_validator(self):
        fields = {"aadhaar_number": "236849758023", "name": "Test", "dob": "01/01/2000", "gender": "MALE"}
        result = validate_document("aadhaar_card", fields)
        assert result["status"] == "success"
        assert result["doc_type"] == "aadhaar_card"
        assert result["score"] > 0

    def test_unknown_doc_type(self):
        result = validate_document("unknown_type", {"field": "value"})
        assert result["status"] == "error"
        assert "No validator" in result["error"]

    def test_none_fields(self):
        result = validate_document("aadhaar_card", None)
        assert result["status"] == "skipped"

    def test_empty_fields(self):
        result = validate_document("pan_card", {})
        # Empty dict is truthy but has no fields — validator runs and flags missing fields
        assert result["status"] in ("success", "skipped")

    def test_all_doc_types_have_validators(self):
        doc_types = ["sppu_marksheet", "aadhaar_card", "pan_card", "experience_certificate"]
        for dt in doc_types:
            result = validate_document(dt, {"dummy": "field"})
            assert result["status"] == "success", f"No validator for {dt}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
