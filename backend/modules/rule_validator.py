"""
Rule-Based Validator — validates extracted document data against domain rules.

Each document type has specific validation functions. Returns structured
pass/fail results with descriptions and severity levels.
"""

import re
from datetime import datetime
from typing import Optional


# ─── Verhoeff Algorithm (Aadhaar checksum) ─────────────────────────

# Multiplication table
VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]

# Permutation table
VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]

# Inverse table
VERHOEFF_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def verhoeff_checksum(number: str) -> bool:
    """
    Validate a number string using the Verhoeff checksum algorithm.
    Returns True if the number has a valid Verhoeff checksum (last digit).
    Used for Aadhaar number validation.
    """
    if not number or not number.isdigit():
        return False
    c = 0
    # Process digits from right to left
    digits = [int(d) for d in reversed(number)]
    for i, digit in enumerate(digits):
        c = VERHOEFF_D[c][VERHOEFF_P[i % 8][digit]]
    return c == 0


# ─── SPPU Grading Scale ────────────────────────────────────────────

SPPU_GRADING_SCALE = {
    "O":  {"min": 91, "max": 100, "grade_points": 10},
    "A+": {"min": 81, "max": 90,  "grade_points": 9},
    "A":  {"min": 71, "max": 80,  "grade_points": 8},
    "B+": {"min": 61, "max": 70,  "grade_points": 7},
    "B":  {"min": 51, "max": 60,  "grade_points": 6},
    "C":  {"min": 41, "max": 50,  "grade_points": 5},
    "F":  {"min": 0,  "max": 40,  "grade_points": 0},
}


def _expected_grade(total_marks: int, max_marks: int = 150) -> Optional[str]:
    """Get expected grade for a given total marks (percentage-based)."""
    if max_marks <= 0:
        return None
    percentage = (total_marks / max_marks) * 100
    for grade, scale in SPPU_GRADING_SCALE.items():
        if scale["min"] <= percentage <= scale["max"]:
            return grade
    return None


def _expected_grade_points(grade: str) -> Optional[float]:
    """Get expected grade points for a given grade."""
    scale = SPPU_GRADING_SCALE.get(grade)
    return scale["grade_points"] if scale else None


# ─── Date Parsing Helper ───────────────────────────────────────────

def _parse_date(date_str: str) -> Optional[datetime]:
    """Try parsing a date string in common Indian document formats."""
    if not date_str:
        return None
    formats = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d %b %Y", "%d %B %Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


# ─── SPPU Marksheet Validation ─────────────────────────────────────

def validate_sppu_marksheet(fields: dict) -> dict:
    """Validate SPPU marksheet extracted fields."""
    passed = []
    failed = []

    # Rule 1: PRN format (11 digits)
    prn = fields.get("prn")
    if prn:
        prn_str = str(prn).strip()
        if re.match(r"^\d{11}$", prn_str):
            passed.append({"rule": "prn_format", "description": "PRN is 11 digits"})
        else:
            failed.append({
                "rule": "prn_format",
                "description": f"PRN '{prn_str}' is not 11 digits",
                "severity": "high",
            })
    else:
        failed.append({
            "rule": "prn_format",
            "description": "PRN is missing",
            "severity": "high",
        })

    # Rule 2: Semester range (1-8)
    semester = fields.get("semester")
    if semester is not None:
        try:
            sem = int(semester)
            if 1 <= sem <= 8:
                passed.append({"rule": "semester_range", "description": f"Semester {sem} is valid (1-8)"})
            else:
                failed.append({
                    "rule": "semester_range",
                    "description": f"Semester {sem} is out of range (expected 1-8)",
                    "severity": "medium",
                })
        except (ValueError, TypeError):
            failed.append({
                "rule": "semester_range",
                "description": f"Semester '{semester}' is not a valid number",
                "severity": "medium",
            })

    # Rule 3: Subject-level validations
    subjects = fields.get("subjects")
    if subjects and isinstance(subjects, list):
        for i, subj in enumerate(subjects):
            if not isinstance(subj, dict):
                continue
            subj_name = subj.get("subject_name", f"Subject {i+1}")

            # 3a: internal + external == total
            internal = subj.get("internal_marks")
            external = subj.get("external_marks")
            total = subj.get("total_marks")
            if internal is not None and external is not None and total is not None:
                try:
                    calc_total = int(internal) + int(external)
                    if calc_total == int(total):
                        passed.append({
                            "rule": "marks_total",
                            "description": f"{subj_name}: internal({internal}) + external({external}) = total({total})",
                        })
                    else:
                        failed.append({
                            "rule": "marks_total",
                            "description": f"{subj_name}: internal({internal}) + external({external}) = {calc_total}, but total shown as {total}",
                            "severity": "high",
                        })
                except (ValueError, TypeError):
                    pass

            # 3b: Grade consistency with total marks
            grade = subj.get("grade")
            if grade and total is not None:
                try:
                    expected = _expected_grade(int(total))
                    if expected and expected == grade:
                        passed.append({
                            "rule": "grade_consistency",
                            "description": f"{subj_name}: grade '{grade}' matches total marks {total}",
                        })
                    elif expected:
                        failed.append({
                            "rule": "grade_consistency",
                            "description": f"{subj_name}: grade '{grade}' doesn't match total marks {total} (expected '{expected}')",
                            "severity": "high",
                        })
                except (ValueError, TypeError):
                    pass

            # 3c: Grade points match grade
            grade_points = subj.get("grade_points")
            if grade and grade_points is not None:
                try:
                    expected_gp = _expected_grade_points(grade)
                    if expected_gp is not None and abs(float(grade_points) - expected_gp) < 0.01:
                        passed.append({
                            "rule": "grade_points_match",
                            "description": f"{subj_name}: grade points {grade_points} match grade '{grade}'",
                        })
                    elif expected_gp is not None:
                        failed.append({
                            "rule": "grade_points_match",
                            "description": f"{subj_name}: grade points {grade_points} don't match grade '{grade}' (expected {expected_gp})",
                            "severity": "high",
                        })
                except (ValueError, TypeError):
                    pass

        # Rule 4: SGPA calculation
        sgpa = fields.get("sgpa")
        if sgpa is not None:
            try:
                total_credit_points = 0
                total_credits = 0
                can_compute = True
                for subj in subjects:
                    if not isinstance(subj, dict):
                        continue
                    credits = subj.get("credits")
                    grade_points = subj.get("grade_points")
                    if credits is not None and grade_points is not None:
                        total_credit_points += float(credits) * float(grade_points)
                        total_credits += float(credits)
                    else:
                        can_compute = False
                        break

                if can_compute and total_credits > 0:
                    computed_sgpa = round(total_credit_points / total_credits, 2)
                    claimed_sgpa = float(sgpa)
                    if abs(computed_sgpa - claimed_sgpa) <= 0.05:
                        passed.append({
                            "rule": "sgpa_calculation",
                            "description": f"SGPA {claimed_sgpa} matches computed value {computed_sgpa}",
                        })
                    else:
                        failed.append({
                            "rule": "sgpa_calculation",
                            "description": f"SGPA {claimed_sgpa} doesn't match computed value {computed_sgpa} (tolerance ±0.05)",
                            "severity": "high",
                        })
            except (ValueError, TypeError):
                pass

        # Rule 5: Result consistency (PASS/FAIL)
        result = fields.get("result")
        if result:
            has_f = any(
                isinstance(s, dict) and s.get("grade") == "F"
                for s in subjects
            )
            result_upper = str(result).upper()
            if result_upper == "PASS" and has_f:
                failed.append({
                    "rule": "result_consistency",
                    "description": "Result is PASS but one or more subjects have grade 'F'",
                    "severity": "high",
                })
            elif result_upper == "FAIL" and not has_f:
                failed.append({
                    "rule": "result_consistency",
                    "description": "Result is FAIL but no subjects have grade 'F'",
                    "severity": "medium",
                })
            else:
                passed.append({
                    "rule": "result_consistency",
                    "description": f"Result '{result_upper}' is consistent with subject grades",
                })

    total_rules = len(passed) + len(failed)
    score = len(passed) / total_rules if total_rules > 0 else 0.0

    return {"score": round(score, 2), "passed": passed, "failed": failed}


# ─── Aadhaar Card Validation ──────────────────────────────────────

def validate_aadhaar_card(fields: dict) -> dict:
    """Validate Aadhaar card extracted fields."""
    passed = []
    failed = []

    # Rule 1: Aadhaar number format (12 digits)
    aadhaar = fields.get("aadhaar_number")
    if aadhaar:
        # Clean spaces/dashes
        clean = re.sub(r"[\s\-]", "", str(aadhaar))
        if re.match(r"^\d{12}$", clean):
            passed.append({"rule": "aadhaar_format", "description": "Aadhaar number is 12 digits"})

            # Rule 2: Verhoeff checksum
            if verhoeff_checksum(clean):
                passed.append({"rule": "aadhaar_verhoeff", "description": "Aadhaar number passes Verhoeff checksum"})
            else:
                failed.append({
                    "rule": "aadhaar_verhoeff",
                    "description": "Aadhaar number fails Verhoeff checksum — likely invalid or tampered",
                    "severity": "high",
                })

            # Rule 3: First digit cannot be 0 or 1
            if clean[0] in ("0", "1"):
                failed.append({
                    "rule": "aadhaar_first_digit",
                    "description": f"Aadhaar number starts with '{clean[0]}' — valid Aadhaar numbers start with 2-9",
                    "severity": "high",
                })
            else:
                passed.append({"rule": "aadhaar_first_digit", "description": "Aadhaar first digit is valid (2-9)"})
        else:
            failed.append({
                "rule": "aadhaar_format",
                "description": f"Aadhaar number '{aadhaar}' is not 12 digits",
                "severity": "high",
            })
    else:
        failed.append({
            "rule": "aadhaar_format",
            "description": "Aadhaar number is missing",
            "severity": "high",
        })

    # Rule 4: Date of birth validation
    dob = fields.get("dob")
    if dob:
        parsed = _parse_date(str(dob))
        if parsed:
            now = datetime.now()
            age = (now - parsed).days / 365.25
            if 0 <= age <= 120:
                passed.append({"rule": "dob_valid", "description": f"Date of birth '{dob}' is valid (age ~{int(age)})"})
            else:
                failed.append({
                    "rule": "dob_valid",
                    "description": f"Date of birth '{dob}' gives unreasonable age ({int(age)} years)",
                    "severity": "medium",
                })
            if parsed > now:
                failed.append({
                    "rule": "dob_future",
                    "description": f"Date of birth '{dob}' is in the future",
                    "severity": "high",
                })
        else:
            failed.append({
                "rule": "dob_valid",
                "description": f"Could not parse date of birth: '{dob}'",
                "severity": "low",
            })

    # Rule 5: Gender field
    gender = fields.get("gender")
    if gender:
        if str(gender).upper() in ("MALE", "FEMALE", "OTHER"):
            passed.append({"rule": "gender_valid", "description": f"Gender '{gender}' is valid"})
        else:
            failed.append({
                "rule": "gender_valid",
                "description": f"Gender '{gender}' is not a standard value (expected MALE/FEMALE/OTHER)",
                "severity": "low",
            })

    # Rule 6: VID format (16 digits if present)
    vid = fields.get("vid")
    if vid:
        clean_vid = re.sub(r"[\s\-]", "", str(vid))
        if re.match(r"^\d{16}$", clean_vid):
            passed.append({"rule": "vid_format", "description": "VID is 16 digits"})
        else:
            failed.append({
                "rule": "vid_format",
                "description": f"VID '{vid}' is not 16 digits",
                "severity": "low",
            })

    total_rules = len(passed) + len(failed)
    score = len(passed) / total_rules if total_rules > 0 else 0.0

    return {"score": round(score, 2), "passed": passed, "failed": failed}


# ─── PAN Card Validation ──────────────────────────────────────────

def validate_pan_card(fields: dict) -> dict:
    """Validate PAN card extracted fields."""
    passed = []
    failed = []

    # Rule 1: PAN format (AAAAA9999A)
    pan = fields.get("pan_number")
    if pan:
        pan_str = str(pan).strip().upper()
        if re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", pan_str):
            passed.append({"rule": "pan_format", "description": f"PAN '{pan_str}' matches format AAAAA9999A"})

            # Rule 2: 4th character indicates entity type
            fourth = pan_str[3]
            entity_types = {
                "P": "Person", "C": "Company", "H": "HUF",
                "F": "Firm", "A": "AOP", "T": "Trust",
                "B": "BOI", "L": "Local Authority",
                "J": "Artificial Juridical Person", "G": "Government",
            }
            if fourth in entity_types:
                passed.append({
                    "rule": "pan_entity_type",
                    "description": f"4th character '{fourth}' = {entity_types[fourth]} (valid entity type)",
                })
            else:
                failed.append({
                    "rule": "pan_entity_type",
                    "description": f"4th character '{fourth}' is not a valid entity type",
                    "severity": "high",
                })

            # Rule 3: 5th character matches surname initial (if name available)
            name = fields.get("name")
            if name and fourth == "P":
                # For individuals, 5th char should match surname initial
                surname_initial = str(name).strip()[0].upper()
                fifth = pan_str[4]
                if fifth == surname_initial:
                    passed.append({
                        "rule": "pan_name_match",
                        "description": f"5th character '{fifth}' matches name initial '{surname_initial}'",
                    })
                else:
                    # This is a soft check — surname could be different from full name ordering
                    failed.append({
                        "rule": "pan_name_match",
                        "description": f"5th character '{fifth}' doesn't match name initial '{surname_initial}' (may use surname)",
                        "severity": "low",
                    })
        else:
            failed.append({
                "rule": "pan_format",
                "description": f"PAN '{pan_str}' doesn't match format AAAAA9999A",
                "severity": "high",
            })
    else:
        failed.append({
            "rule": "pan_format",
            "description": "PAN number is missing",
            "severity": "high",
        })

    # Rule 4: Date of birth
    dob = fields.get("dob")
    if dob:
        parsed = _parse_date(str(dob))
        if parsed:
            now = datetime.now()
            if parsed <= now:
                passed.append({"rule": "dob_valid", "description": f"Date of birth '{dob}' is valid"})
            else:
                failed.append({
                    "rule": "dob_valid",
                    "description": f"Date of birth '{dob}' is in the future",
                    "severity": "high",
                })
        else:
            failed.append({
                "rule": "dob_valid",
                "description": f"Could not parse date of birth: '{dob}'",
                "severity": "low",
            })

    # Rule 5: Name present
    name = fields.get("name")
    if name and len(str(name).strip()) > 1:
        passed.append({"rule": "name_present", "description": "Name field is present"})
    else:
        failed.append({
            "rule": "name_present",
            "description": "Name is missing or too short",
            "severity": "medium",
        })

    total_rules = len(passed) + len(failed)
    score = len(passed) / total_rules if total_rules > 0 else 0.0

    return {"score": round(score, 2), "passed": passed, "failed": failed}


# ─── Experience Certificate Validation ─────────────────────────────

def validate_experience_certificate(fields: dict) -> dict:
    """Validate experience certificate extracted fields."""
    passed = []
    failed = []

    # Rule 1: Date of joining < Date of relieving
    joining = fields.get("date_of_joining")
    relieving = fields.get("date_of_relieving")
    parsed_joining = _parse_date(str(joining)) if joining else None
    parsed_relieving = _parse_date(str(relieving)) if relieving else None

    if parsed_joining and parsed_relieving:
        if parsed_relieving > parsed_joining:
            passed.append({
                "rule": "dates_order",
                "description": f"Relieving date ({relieving}) is after joining date ({joining})",
            })

            # Rule 2: Duration consistency
            duration = fields.get("duration")
            if duration:
                actual_months = (parsed_relieving.year - parsed_joining.year) * 12 + (parsed_relieving.month - parsed_joining.month)
                # Try to extract months/years from duration string
                duration_str = str(duration).lower()
                claimed_months = 0
                year_match = re.search(r"(\d+)\s*year", duration_str)
                month_match = re.search(r"(\d+)\s*month", duration_str)
                if year_match:
                    claimed_months += int(year_match.group(1)) * 12
                if month_match:
                    claimed_months += int(month_match.group(1))

                if claimed_months > 0:
                    diff = abs(actual_months - claimed_months)
                    if diff <= 1:
                        passed.append({
                            "rule": "duration_consistency",
                            "description": f"Claimed duration '{duration}' matches date range ({actual_months} months)",
                        })
                    else:
                        failed.append({
                            "rule": "duration_consistency",
                            "description": f"Claimed duration '{duration}' ({claimed_months} months) doesn't match date range ({actual_months} months)",
                            "severity": "medium",
                        })
        else:
            failed.append({
                "rule": "dates_order",
                "description": f"Relieving date ({relieving}) is before or same as joining date ({joining})",
                "severity": "high",
            })
    else:
        if not parsed_joining and joining:
            failed.append({
                "rule": "date_parse",
                "description": f"Could not parse joining date: '{joining}'",
                "severity": "low",
            })
        if not parsed_relieving and relieving:
            failed.append({
                "rule": "date_parse",
                "description": f"Could not parse relieving date: '{relieving}'",
                "severity": "low",
            })
        if not joining:
            failed.append({
                "rule": "date_missing",
                "description": "Date of joining is missing",
                "severity": "medium",
            })
        if not relieving:
            failed.append({
                "rule": "date_missing",
                "description": "Date of relieving is missing",
                "severity": "medium",
            })

    # Rule 3: Dates not in the future
    now = datetime.now()
    if parsed_joining and parsed_joining > now:
        failed.append({
            "rule": "joining_future",
            "description": f"Joining date ({joining}) is in the future",
            "severity": "high",
        })
    if parsed_relieving and parsed_relieving > now:
        failed.append({
            "rule": "relieving_future",
            "description": f"Relieving date ({relieving}) is in the future",
            "severity": "medium",
        })

    # Rule 4: Employee name present
    emp_name = fields.get("employee_name")
    if emp_name and len(str(emp_name).strip()) > 1:
        passed.append({"rule": "employee_name_present", "description": "Employee name is present"})
    else:
        failed.append({
            "rule": "employee_name_present",
            "description": "Employee name is missing",
            "severity": "high",
        })

    # Rule 5: Company name present
    company = fields.get("company_name")
    if company and len(str(company).strip()) > 1:
        passed.append({"rule": "company_name_present", "description": "Company name is present"})
    else:
        failed.append({
            "rule": "company_name_present",
            "description": "Company name is missing",
            "severity": "medium",
        })

    total_rules = len(passed) + len(failed)
    score = len(passed) / total_rules if total_rules > 0 else 0.0

    return {"score": round(score, 2), "passed": passed, "failed": failed}


# ─── Main Entry Point ──────────────────────────────────────────────

VALIDATORS = {
    "sppu_marksheet": validate_sppu_marksheet,
    "aadhaar_card": validate_aadhaar_card,
    "pan_card": validate_pan_card,
    "experience_certificate": validate_experience_certificate,
}


def validate_document(doc_type: str, extracted_fields: dict) -> dict:
    """
    Run rule-based validation on extracted document fields.

    Args:
        doc_type: Document type string.
        extracted_fields: Dict of fields extracted by OCR.

    Returns:
        Dict with keys: score, passed, failed, doc_type, status
    """
    if not extracted_fields:
        return {
            "score": 0.0,
            "passed": [],
            "failed": [],
            "doc_type": doc_type,
            "status": "skipped",
            "error": "No extracted fields to validate",
        }

    validator = VALIDATORS.get(doc_type)
    if not validator:
        return {
            "score": 0.0,
            "passed": [],
            "failed": [],
            "doc_type": doc_type,
            "status": "error",
            "error": f"No validator for document type: {doc_type}",
        }

    try:
        result = validator(extracted_fields)
        result["doc_type"] = doc_type
        result["status"] = "success"
        result["error"] = None
        return result
    except Exception as e:
        return {
            "score": 0.0,
            "passed": [],
            "failed": [],
            "doc_type": doc_type,
            "status": "error",
            "error": f"Validation failed: {str(e)}",
        }
