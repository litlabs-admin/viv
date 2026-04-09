"""
Score Aggregator — combines all module scores into a final verdict.

Weights:
    CNN forgery:  40%
    Rule-based:   25%
    NLP:          15%
    Anomaly:      10%
    OCR:          10%

Hard override rules:
    - Any critical rule failure → FRAUDULENT
    - CNN forgery probability > 0.90 → at least NEEDS_REVIEW

Verdict thresholds:
    0.85 - 1.00 → VERIFIED (green)
    0.65 - 0.84 → NEEDS_REVIEW (yellow)
    0.00 - 0.64 → FRAUDULENT (red)
"""


WEIGHTS = {
    "cnn": 0.40,
    "rule": 0.25,
    "nlp": 0.15,
    "anomaly": 0.10,
    "ocr": 0.10,
}

VERDICT_THRESHOLDS = {
    "VERIFIED": 0.85,
    "NEEDS_REVIEW": 0.65,
}


def aggregate_scores(
    cnn_forgery_probability: float = 0.0,
    rule_score: float = 0.0,
    nlp_score: float = 0.0,
    anomaly_score: float = 0.0,
    ocr_confidence: float = 0.0,
    failed_rules: list = None,
) -> dict:
    """
    Combine all module scores into a final confidence score and verdict.

    Args:
        cnn_forgery_probability: 0-1, higher = more likely forged
        rule_score: 0-1, higher = more rules passed
        nlp_score: 0-1, higher = more consistent
        anomaly_score: 0-1, higher = more anomalous
        ocr_confidence: 0-1, higher = more confident OCR

    Returns:
        Dict with: final_score, verdict, verdict_color, module_scores, override_reason
    """
    if failed_rules is None:
        failed_rules = []

    # Calculate weighted score
    # CNN and anomaly are inverted (high probability = bad)
    final_score = (
        WEIGHTS["cnn"] * (1.0 - cnn_forgery_probability) +
        WEIGHTS["rule"] * rule_score +
        WEIGHTS["nlp"] * nlp_score +
        WEIGHTS["anomaly"] * (1.0 - anomaly_score) +
        WEIGHTS["ocr"] * ocr_confidence
    )
    final_score = round(max(0.0, min(1.0, final_score)), 4)

    # Module scores breakdown
    module_scores = {
        "cnn_forgery": {
            "raw": round(cnn_forgery_probability, 4),
            "weighted": round(WEIGHTS["cnn"] * (1.0 - cnn_forgery_probability), 4),
            "weight": WEIGHTS["cnn"],
        },
        "rule_validation": {
            "raw": round(rule_score, 4),
            "weighted": round(WEIGHTS["rule"] * rule_score, 4),
            "weight": WEIGHTS["rule"],
        },
        "nlp_consistency": {
            "raw": round(nlp_score, 4),
            "weighted": round(WEIGHTS["nlp"] * nlp_score, 4),
            "weight": WEIGHTS["nlp"],
        },
        "anomaly_detection": {
            "raw": round(anomaly_score, 4),
            "weighted": round(WEIGHTS["anomaly"] * (1.0 - anomaly_score), 4),
            "weight": WEIGHTS["anomaly"],
        },
        "ocr_confidence": {
            "raw": round(ocr_confidence, 4),
            "weighted": round(WEIGHTS["ocr"] * ocr_confidence, 4),
            "weight": WEIGHTS["ocr"],
        },
    }

    # Determine verdict
    override_reason = None

    # Hard override: critical rule failures
    critical_failures = [
        rule for rule in failed_rules
        if isinstance(rule, dict) and rule.get("severity") == "high"
    ]
    if critical_failures:
        # If many critical failures, force FRAUDULENT
        if len(critical_failures) >= 3:
            final_score = min(final_score, 0.60)
            override_reason = f"{len(critical_failures)} critical rule failures detected"

    # Hard override: very high forgery probability
    if cnn_forgery_probability > 0.90:
        if final_score >= VERDICT_THRESHOLDS["VERIFIED"]:
            final_score = min(final_score, 0.80)
            override_reason = "CNN forgery probability > 90% — overriding to NEEDS_REVIEW"

    # Determine verdict from final score
    if final_score >= VERDICT_THRESHOLDS["VERIFIED"]:
        verdict = "VERIFIED"
        verdict_color = "green"
    elif final_score >= VERDICT_THRESHOLDS["NEEDS_REVIEW"]:
        verdict = "NEEDS_REVIEW"
        verdict_color = "yellow"
    else:
        verdict = "FRAUDULENT"
        verdict_color = "red"

    return {
        "final_score": final_score,
        "verdict": verdict,
        "verdict_color": verdict_color,
        "module_scores": module_scores,
        "weights": WEIGHTS,
        "override_reason": override_reason,
    }
