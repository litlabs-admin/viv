"""
NLP Semantic Consistency Checker

Validates extracted document data for:
1. Entity consistency — names, dates appear consistently across fields
2. Institution validity — college name fuzzy-matches known SPPU colleges
3. Cross-field logic — temporal consistency (DoB < graduation < experience)

Uses spaCy for NER when available, falls back to regex-based extraction.
"""

import re
from datetime import datetime
from typing import Optional

# spaCy — optional, gracefully handle if not installed
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

# fuzzywuzzy — optional
try:
    from fuzzywuzzy import fuzz
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False


# ─── spaCy Model Loading ─────────────────────────────────────────

_nlp_model = None


def _get_nlp():
    """Load spaCy model (lazy singleton)."""
    global _nlp_model
    if _nlp_model is not None:
        return _nlp_model
    if not SPACY_AVAILABLE:
        return None
    try:
        _nlp_model = spacy.load("en_core_web_sm")
        return _nlp_model
    except OSError:
        return None


# ─── Known SPPU-Affiliated Colleges ──────────────────────────────

SPPU_COLLEGES = [
    "College of Engineering Pune",
    "COEP Technological University",
    "Pune Institute of Computer Technology",
    "PICT",
    "Vishwakarma Institute of Technology",
    "VIT Pune",
    "Cummins College of Engineering",
    "Sinhgad College of Engineering",
    "MIT College of Engineering",
    "MITCOE",
    "Maharashtra Institute of Technology",
    "Army Institute of Technology",
    "AIT Pune",
    "Bharati Vidyapeeth College of Engineering",
    "BVCOE",
    "Pimpri Chinchwad College of Engineering",
    "PCCoE",
    "NBN Sinhgad School of Engineering",
    "DYPCOE",
    "D.Y. Patil College of Engineering",
    "JSPM Narhe Technical Campus",
    "JSPM Rajarshi Shahu College of Engineering",
    "Indira College of Engineering and Management",
    "ICEM",
    "Modern Education Society College of Engineering",
    "MESCE",
    "Zeal College of Engineering",
    "Smt. Kashibai Navale College of Engineering",
    "SKNCOE",
    "Savitribai Phule Pune University",
    "SPPU",
    "Walchand College of Engineering",
    "Government College of Engineering Pune",
    "International Institute of Information Technology Pune",
    "IIIT Pune",
    "Symbiosis Institute of Technology",
    "SIT Pune",
    "RMD Sinhgad School of Engineering",
    "Trinity College of Engineering",
    "AISSMS College of Engineering",
    "PES Modern College of Engineering",
]


# ─── Date Parsing ────────────────────────────────────────────────

def _parse_date(date_str: str) -> Optional[datetime]:
    """Parse a date string in common Indian document formats."""
    if not date_str:
        return None
    formats = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d %b %Y", "%d %B %Y",
               "%m/%Y", "%B %Y", "%b %Y", "%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(str(date_str).strip(), fmt)
        except ValueError:
            continue
    return None


# ─── Entity Extraction (NER) ─────────────────────────────────────

def extract_entities_spacy(text: str) -> dict:
    """Extract named entities using spaCy NER."""
    nlp = _get_nlp()
    if nlp is None:
        return {"persons": [], "orgs": [], "dates": []}

    doc = nlp(text)
    persons = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
    orgs = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
    dates = [ent.text for ent in doc.ents if ent.label_ == "DATE"]

    return {"persons": persons, "orgs": orgs, "dates": dates}


def extract_entities_regex(text: str) -> dict:
    """Fallback: extract entities using regex patterns."""
    # Date patterns
    date_patterns = [
        r"\d{2}[/-]\d{2}[/-]\d{4}",
        r"\d{4}[/-]\d{2}[/-]\d{2}",
        r"\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}",
    ]
    dates = []
    for pattern in date_patterns:
        dates.extend(re.findall(pattern, text, re.IGNORECASE))

    return {"persons": [], "orgs": [], "dates": dates}


# ─── Name Consistency Check ──────────────────────────────────────

def _normalize_name(name: str) -> str:
    """Normalize a name for comparison."""
    if not name:
        return ""
    return re.sub(r"\s+", " ", str(name).strip().upper())


def check_name_consistency(fields: dict) -> list:
    """
    Check that name fields are consistent across the document.
    Returns list of findings (strings).
    """
    findings = []

    # Collect all name-related fields
    name_fields = {}
    for key in ["name", "student_name", "employee_name", "candidate_name",
                 "father_name", "fathers_name", "mother_name"]:
        val = fields.get(key)
        if val and len(str(val).strip()) > 1:
            name_fields[key] = _normalize_name(val)

    # Check primary name appears in at least one field
    primary_name = name_fields.get("name") or name_fields.get("student_name") or name_fields.get("employee_name")
    if not primary_name:
        findings.append("No primary name field found in document")
        return findings

    # Check name contains at least first and last name (2+ parts)
    parts = primary_name.split()
    if len(parts) < 2:
        findings.append(f"Name '{primary_name}' appears to have only one part (expected first + last name)")

    # Check father's name is different from candidate name
    father = name_fields.get("father_name") or name_fields.get("fathers_name")
    if father and primary_name:
        if father == primary_name:
            findings.append(f"Father's name '{father}' is identical to candidate name — suspicious")

    return findings


# ─── Date Consistency Check ──────────────────────────────────────

def check_date_consistency(fields: dict, doc_type: str) -> list:
    """
    Check temporal consistency of dates in the document.
    - DoB should be before any other dates
    - Joining date should be before relieving date
    - Exam date should be after DoB
    """
    findings = []

    dob = _parse_date(str(fields.get("dob", "")))

    if doc_type == "sppu_marksheet":
        exam_date = _parse_date(str(fields.get("exam_date", "")))
        if dob and exam_date:
            if exam_date <= dob:
                findings.append(f"Exam date is before or same as date of birth — impossible")
            else:
                age_at_exam = (exam_date - dob).days / 365.25
                if age_at_exam < 15:
                    findings.append(f"Student was only {age_at_exam:.0f} years old at exam — unusually young")
                elif age_at_exam > 60:
                    findings.append(f"Student was {age_at_exam:.0f} years old at exam — unusually old")

    elif doc_type == "experience_certificate":
        joining = _parse_date(str(fields.get("date_of_joining", "")))
        relieving = _parse_date(str(fields.get("date_of_relieving", "")))

        if dob and joining:
            age_at_joining = (joining - dob).days / 365.25
            if age_at_joining < 16:
                findings.append(f"Employee was {age_at_joining:.0f} years old at joining — below minimum working age")

        if joining and relieving:
            tenure = (relieving - joining).days / 365.25
            if tenure > 50:
                findings.append(f"Tenure of {tenure:.0f} years is unusually long")

    elif doc_type == "aadhaar_card":
        if dob:
            now = datetime.now()
            age = (now - dob).days / 365.25
            if age < 0:
                findings.append("Date of birth is in the future")
            elif age > 120:
                findings.append(f"Age of {age:.0f} years is impossibly high")

    elif doc_type == "pan_card":
        if dob:
            now = datetime.now()
            age = (now - dob).days / 365.25
            if age < 18:
                findings.append(f"PAN holder is only {age:.0f} years old — PAN is typically issued to adults")

    return findings


# ─── Institution Validity Check ──────────────────────────────────

def check_institution_validity(fields: dict) -> list:
    """
    Check if the college/institution name fuzzy-matches known SPPU colleges.
    Returns list of findings.
    """
    findings = []
    college = fields.get("college_name") or fields.get("institution")
    if not college:
        return findings

    college_str = str(college).strip()
    if not college_str:
        return findings

    if not FUZZY_AVAILABLE:
        # Basic substring check fallback
        college_upper = college_str.upper()
        matched = False
        for known in SPPU_COLLEGES:
            if known.upper() in college_upper or college_upper in known.upper():
                matched = True
                break
        if not matched:
            findings.append(f"College '{college_str}' not found in known SPPU colleges list (basic check)")
        return findings

    # Fuzzy matching
    best_score = 0
    best_match = ""
    for known in SPPU_COLLEGES:
        score = fuzz.token_set_ratio(college_str.lower(), known.lower())
        if score > best_score:
            best_score = score
            best_match = known

    if best_score >= 80:
        # Good match — no finding needed (or positive finding)
        pass
    elif best_score >= 50:
        findings.append(
            f"College '{college_str}' partially matches '{best_match}' "
            f"(score: {best_score}/100) — verify manually"
        )
    else:
        findings.append(
            f"College '{college_str}' does not match any known SPPU college "
            f"(best match: '{best_match}' at {best_score}/100)"
        )

    return findings


# ─── Field Completeness Check ────────────────────────────────────

REQUIRED_FIELDS = {
    "sppu_marksheet": ["student_name", "prn", "semester", "subjects", "sgpa"],
    "aadhaar_card": ["aadhaar_number", "name", "dob"],
    "pan_card": ["pan_number", "name", "dob"],
    "experience_certificate": ["employee_name", "company_name", "date_of_joining", "date_of_relieving"],
}


def check_field_completeness(fields: dict, doc_type: str) -> list:
    """Check if all required fields are present and non-empty."""
    findings = []
    required = REQUIRED_FIELDS.get(doc_type, [])

    missing = []
    for field in required:
        val = fields.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing.append(field)

    if missing:
        findings.append(f"Missing required fields: {', '.join(missing)}")

    return findings


# ─── Main NLP Check Function ────────────────────────────────────


def check_nlp_consistency(extracted_fields: dict, doc_type: str) -> dict:
    """
    Run NLP-based semantic consistency checks on extracted document data.

    Args:
        extracted_fields: Dict of fields from OCR extraction.
        doc_type: Document type string.

    Returns:
        Dict with keys: score, findings, status, error
    """
    if not extracted_fields:
        return {
            "score": 0.0,
            "findings": [],
            "status": "skipped",
            "error": "No extracted fields to check",
        }

    try:
        all_findings = []

        # 1. Name consistency
        name_findings = check_name_consistency(extracted_fields)
        all_findings.extend(name_findings)

        # 2. Date consistency
        date_findings = check_date_consistency(extracted_fields, doc_type)
        all_findings.extend(date_findings)

        # 3. Institution validity (only for marksheets)
        if doc_type == "sppu_marksheet":
            inst_findings = check_institution_validity(extracted_fields)
            all_findings.extend(inst_findings)

        # 4. Field completeness
        completeness_findings = check_field_completeness(extracted_fields, doc_type)
        all_findings.extend(completeness_findings)

        # 5. spaCy NER cross-check (if available)
        if SPACY_AVAILABLE and _get_nlp() is not None:
            # Build text from all string fields for NER
            text_parts = []
            for key, val in extracted_fields.items():
                if isinstance(val, str) and len(val) > 2:
                    text_parts.append(val)
            full_text = " ".join(text_parts)
            if full_text.strip():
                entities = extract_entities_spacy(full_text)
                # Check if NER found person names that don't match declared name
                declared_name = _normalize_name(
                    extracted_fields.get("name", "")
                    or extracted_fields.get("student_name", "")
                    or extracted_fields.get("employee_name", "")
                )
                if declared_name and entities["persons"]:
                    ner_names = [_normalize_name(n) for n in entities["persons"]]
                    # Check if any NER name contradicts declared name
                    for ner_name in ner_names:
                        if ner_name and len(ner_name) > 3:
                            # Check if it shares at least one word with declared name
                            ner_parts = set(ner_name.split())
                            declared_parts = set(declared_name.split())
                            if not ner_parts.intersection(declared_parts):
                                all_findings.append(
                                    f"NER detected name '{ner_name}' that doesn't match "
                                    f"declared name '{declared_name}'"
                                )

        # Calculate score: fewer findings = higher score
        if len(all_findings) == 0:
            score = 1.0
        elif len(all_findings) <= 2:
            score = 0.7
        elif len(all_findings) <= 4:
            score = 0.4
        else:
            score = 0.2

        return {
            "score": round(score, 2),
            "findings": all_findings,
            "status": "success",
            "error": None,
        }

    except Exception as e:
        return {
            "score": 0.0,
            "findings": [],
            "status": "error",
            "error": f"NLP check failed: {str(e)}",
        }
