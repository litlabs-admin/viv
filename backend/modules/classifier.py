"""
Document Type Classifier

Uses LM Studio vision model as primary classifier, with keyword-based
fallback from extracted text.
"""

import re

from modules.ocr_engine import call_lm_studio, extract_raw_text


# Valid document types
VALID_DOC_TYPES = {
    "sppu_marksheet",
    "aadhaar_card",
    "pan_card",
    "experience_certificate",
}

CLASSIFICATION_PROMPT = """Look at this document image carefully.
What type of Indian document is this?

Reply with ONLY one of these exact strings (no other text):
- sppu_marksheet
- aadhaar_card
- pan_card
- experience_certificate

If you are not sure, make your best guess from the options above."""


# Keyword patterns for fallback classification
KEYWORD_PATTERNS = {
    "sppu_marksheet": [
        r"savitribai\s+phule",
        r"\bsppu\b",
        r"\bsgpa\b",
        r"\bprn\b",
        r"grade\s+points?",
        r"semester.*exam",
        r"pune\s+university",
    ],
    "aadhaar_card": [
        r"\baadhaar\b",
        r"\buidai\b",
        r"unique\s+identification",
        r"government\s+of\s+india",
        r"\b\d{4}\s+\d{4}\s+\d{4}\b",  # 12-digit pattern with spaces
    ],
    "pan_card": [
        r"permanent\s+account\s+number",
        r"income\s+tax",
        r"\bpan\b.*\b[A-Z]{5}\d{4}[A-Z]\b",
        r"govt\.?\s+of\s+india",
        r"\b[A-Z]{5}\d{4}[A-Z]\b",  # PAN format
    ],
    "experience_certificate": [
        r"experience\s+certificate",
        r"relieving\s+(letter|certificate)",
        r"hereby\s+certif",
        r"date\s+of\s+joining",
        r"worked\s+with\s+us",
        r"employment\s+certificate",
    ],
}


def classify_by_keywords(text: str) -> dict:
    """
    Classify document type using keyword pattern matching on extracted text.

    Returns dict with doc_type, confidence, and matched_keywords.
    """
    if not text:
        return {"doc_type": "unknown", "confidence": 0.0, "matched_keywords": []}

    text_lower = text.lower()
    scores = {}

    for doc_type, patterns in KEYWORD_PATTERNS.items():
        matches = []
        for pattern in patterns:
            if re.search(pattern, text_lower):
                matches.append(pattern)
        scores[doc_type] = len(matches)

    if not any(scores.values()):
        return {"doc_type": "unknown", "confidence": 0.0, "matched_keywords": []}

    best_type = max(scores, key=scores.get)
    total_patterns = len(KEYWORD_PATTERNS[best_type])
    confidence = min(scores[best_type] / max(total_patterns * 0.5, 1), 1.0)

    return {
        "doc_type": best_type,
        "confidence": round(confidence, 2),
        "matched_keywords": [
            p
            for p in KEYWORD_PATTERNS[best_type]
            if re.search(p, text_lower)
        ],
    }


def classify_by_vision(image_path: str) -> dict:
    """
    Classify document type using LM Studio vision model.

    Returns dict with doc_type, confidence, and method.
    """
    try:
        response = call_lm_studio(image_path, CLASSIFICATION_PROMPT)
        response_clean = response.strip().lower().replace(" ", "_")

        # Try to find a valid doc type in the response
        for valid_type in VALID_DOC_TYPES:
            if valid_type in response_clean:
                return {
                    "doc_type": valid_type,
                    "confidence": 0.85,
                    "method": "vision",
                    "raw_response": response.strip(),
                }

        return {
            "doc_type": "unknown",
            "confidence": 0.0,
            "method": "vision",
            "raw_response": response.strip(),
        }
    except Exception as e:
        return {
            "doc_type": "unknown",
            "confidence": 0.0,
            "method": "vision",
            "error": str(e),
        }


def classify_document(image_path: str) -> dict:
    """
    Classify a document image using vision model first, keyword fallback second.

    Args:
        image_path: Path to the document image.

    Returns:
        Dict with:
            - doc_type: classified document type string
            - confidence: confidence score 0-1
            - method: 'vision', 'keyword', or 'combined'
    """
    # Try vision-based classification first
    vision_result = classify_by_vision(image_path)

    if vision_result["doc_type"] != "unknown":
        return vision_result

    # Fallback: extract raw text and use keywords
    text_result = extract_raw_text(image_path)
    if text_result["status"] == "success" and text_result["text"]:
        keyword_result = classify_by_keywords(text_result["text"])
        keyword_result["method"] = "keyword"
        return keyword_result

    return {
        "doc_type": "unknown",
        "confidence": 0.0,
        "method": "failed",
        "error": "Both vision and keyword classification failed",
    }
