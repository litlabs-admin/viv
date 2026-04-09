"""
Report Generator — produces a structured verification report.

Generates:
1. JSON report with all module results
2. Plain-English summary (uses LM Studio if available, otherwise template-based)
3. Annotated image with forgery highlights (if any)
"""

import os
import json
from datetime import datetime

import cv2
import numpy as np

from config import BASE_DIR, OUTPUT_DIR


def generate_summary_text(verdict: str, final_score: float, doc_type: str,
                          failed_rules: list, nlp_findings: list,
                          forgery_detected: bool, forgery_probability: float,
                          is_anomaly: bool) -> str:
    """
    Generate a plain-English summary of the verification results.
    Template-based (no LLM call needed — fast and reliable for demo).
    """
    doc_names = {
        "sppu_marksheet": "SPPU Marksheet",
        "aadhaar_card": "Aadhaar Card",
        "pan_card": "PAN Card",
        "experience_certificate": "Experience Certificate",
    }
    doc_name = doc_names.get(doc_type, "Document")

    # Opening sentence
    if verdict == "VERIFIED":
        summary = f"The {doc_name} has been verified as authentic with a confidence score of {final_score:.0%}. "
    elif verdict == "NEEDS_REVIEW":
        summary = f"The {doc_name} requires manual review. Confidence score: {final_score:.0%}. "
    else:
        summary = f"The {doc_name} has been flagged as potentially fraudulent with a confidence score of {final_score:.0%}. "

    # Details
    reasons = []

    if forgery_detected:
        reasons.append(f"CNN forgery detection flagged the document with {forgery_probability:.0%} probability of tampering")
    elif forgery_probability > 0.3:
        reasons.append(f"CNN analysis shows moderate forgery indicators ({forgery_probability:.0%})")

    critical_failures = [r for r in failed_rules if isinstance(r, dict) and r.get("severity") == "high"]
    if critical_failures:
        descriptions = [r.get("description", r.get("rule", "unknown")) for r in critical_failures[:3]]
        reasons.append(f"Failed critical validation rules: {'; '.join(descriptions)}")

    if nlp_findings:
        reasons.append(f"Semantic analysis found {len(nlp_findings)} inconsistency(ies): {'; '.join(nlp_findings[:2])}")

    if is_anomaly:
        reasons.append("Statistical anomaly detected — values fall outside expected ranges")

    if reasons:
        summary += "Key findings: " + ". ".join(reasons) + "."
    elif verdict == "VERIFIED":
        summary += "All validation checks passed successfully with no anomalies detected."

    return summary


def generate_annotated_image(image_path: str, forgery_detected: bool,
                             verdict: str, document_id: str) -> str:
    """
    Create an annotated version of the document image.
    Adds a verdict banner and border color.

    Returns path to the saved annotated image.
    """
    img = cv2.imread(image_path)
    if img is None:
        return None

    h, w = img.shape[:2]

    # Add colored border based on verdict
    border_colors = {
        "VERIFIED": (0, 200, 0),       # Green (BGR)
        "NEEDS_REVIEW": (0, 180, 230),  # Yellow (BGR)
        "FRAUDULENT": (0, 0, 230),      # Red (BGR)
    }
    color = border_colors.get(verdict, (200, 200, 200))
    border_size = max(4, min(h, w) // 100)

    annotated = cv2.copyMakeBorder(
        img, border_size, border_size + 40, border_size, border_size,
        cv2.BORDER_CONSTANT, value=color
    )

    # Add verdict text at bottom
    text = f"VERDICT: {verdict}"
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = max(0.5, min(h, w) / 800)
    thickness = max(1, int(font_scale * 2))

    text_y = annotated.shape[0] - 10
    text_x = border_size + 10
    cv2.putText(annotated, text, (text_x, text_y), font, font_scale,
                (255, 255, 255), thickness)

    # Save
    os.makedirs(str(OUTPUT_DIR), exist_ok=True)
    output_path = os.path.join(str(OUTPUT_DIR), f"{document_id}_annotated.jpg")
    cv2.imwrite(output_path, annotated)

    return output_path


def generate_report(
    document_id: str,
    doc_type: str,
    image_path: str,
    preprocessing_result: dict,
    classification_result: dict,
    ocr_result: dict,
    rule_result: dict,
    nlp_result: dict,
    forgery_result: dict,
    anomaly_result: dict,
    aggregation_result: dict,
) -> dict:
    """
    Generate the final verification report.

    Returns:
        Dict with: summary, annotated_image_path, full_report, verdict, final_score
    """
    verdict = aggregation_result.get("verdict", "NEEDS_REVIEW")
    final_score = aggregation_result.get("final_score", 0.0)

    # Generate summary text
    summary = generate_summary_text(
        verdict=verdict,
        final_score=final_score,
        doc_type=doc_type,
        failed_rules=rule_result.get("failed", []),
        nlp_findings=nlp_result.get("findings", []),
        forgery_detected=forgery_result.get("forgery_detected", False),
        forgery_probability=forgery_result.get("forgery_probability", 0.0),
        is_anomaly=anomaly_result.get("is_anomaly", False),
    )

    # Generate annotated image
    annotated_path = None
    if image_path:
        annotated_path = generate_annotated_image(
            image_path, forgery_result.get("forgery_detected", False),
            verdict, document_id,
        )

    # Full report JSON
    full_report = {
        "document_id": document_id,
        "doc_type": doc_type,
        "timestamp": datetime.utcnow().isoformat(),
        "verdict": verdict,
        "final_score": final_score,
        "summary": summary,
        "module_scores": aggregation_result.get("module_scores", {}),
        "weights": aggregation_result.get("weights", {}),
        "override_reason": aggregation_result.get("override_reason"),
        "preprocessing": {
            "status": preprocessing_result.get("status"),
        },
        "classification": {
            "doc_type": doc_type,
            "confidence": classification_result.get("confidence", 0),
            "method": classification_result.get("method", "unknown"),
        },
        "ocr": {
            "status": ocr_result.get("status"),
            "extracted_fields": ocr_result.get("extracted_fields"),
        },
        "rule_validation": {
            "status": rule_result.get("status"),
            "score": rule_result.get("score", 0.0),
            "passed_count": len(rule_result.get("passed", [])),
            "failed_count": len(rule_result.get("failed", [])),
            "passed": rule_result.get("passed", []),
            "failed": rule_result.get("failed", []),
        },
        "nlp_consistency": {
            "status": nlp_result.get("status"),
            "score": nlp_result.get("score", 0.0),
            "findings": nlp_result.get("findings", []),
        },
        "cnn_forgery": {
            "status": forgery_result.get("status"),
            "forgery_detected": forgery_result.get("forgery_detected", False),
            "forgery_probability": forgery_result.get("forgery_probability", 0.0),
            "method": forgery_result.get("method"),
        },
        "anomaly_detection": {
            "status": anomaly_result.get("status"),
            "anomaly_score": anomaly_result.get("anomaly_score", 0.0),
            "is_anomaly": anomaly_result.get("is_anomaly", False),
            "method": anomaly_result.get("method"),
        },
    }

    return {
        "summary": summary,
        "annotated_image_path": annotated_path,
        "full_report": full_report,
        "verdict": verdict,
        "final_score": final_score,
    }
