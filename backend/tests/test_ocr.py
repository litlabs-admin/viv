"""Tests for OCR engine and document classifier modules."""

import os
import sys
import json
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.ocr_engine import (
    image_to_base64,
    get_image_mime_type,
    load_template,
    build_extraction_prompt,
    build_raw_text_prompt,
    parse_json_response,
    extract_document_data,
    extract_raw_text,
)
from modules.classifier import (
    classify_by_keywords,
    classify_document,
    VALID_DOC_TYPES,
)


# ─── OCR Engine Tests ───────────────────────────────────────────────


class TestImageHelpers:
    def test_get_mime_type_jpg(self):
        assert get_image_mime_type("photo.jpg") == "image/jpeg"
        assert get_image_mime_type("photo.jpeg") == "image/jpeg"

    def test_get_mime_type_png(self):
        assert get_image_mime_type("photo.png") == "image/png"

    def test_get_mime_type_unknown_defaults_jpeg(self):
        assert get_image_mime_type("file.bmp") == "image/jpeg"

    def test_image_to_base64(self, tmp_path):
        # Create a small test file
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"\xff\xd8\xff\xe0test image data")
        result = image_to_base64(str(test_file))
        assert isinstance(result, str)
        assert len(result) > 0


class TestTemplateLoading:
    def test_load_sppu_template(self):
        template = load_template("sppu_marksheet")
        assert template is not None
        assert template["document_type"] == "sppu_marksheet"
        assert "fields" in template
        assert "prn" in template["fields"]

    def test_load_aadhaar_template(self):
        template = load_template("aadhaar_card")
        assert template is not None
        assert template["document_type"] == "aadhaar_card"
        assert "aadhaar_number" in template["fields"]

    def test_load_pan_template(self):
        template = load_template("pan_card")
        assert template is not None
        assert "pan_number" in template["fields"]

    def test_load_experience_template(self):
        template = load_template("experience_certificate")
        assert template is not None
        assert "employee_name" in template["fields"]

    def test_load_invalid_type_returns_none(self):
        assert load_template("invalid_type") is None


class TestPromptBuilding:
    def test_extraction_prompt_contains_fields(self):
        template = load_template("sppu_marksheet")
        prompt = build_extraction_prompt("sppu_marksheet", template)
        assert "prn" in prompt
        assert "student_name" in prompt
        assert "sgpa" in prompt
        assert "JSON" in prompt

    def test_raw_text_prompt(self):
        prompt = build_raw_text_prompt()
        assert "text" in prompt.lower()
        assert "extract" in prompt.lower()


class TestJsonParsing:
    def test_parse_clean_json(self):
        result = parse_json_response('{"name": "John", "age": 25}')
        assert result == {"name": "John", "age": 25}

    def test_parse_json_in_code_block(self):
        text = '```json\n{"name": "John"}\n```'
        result = parse_json_response(text)
        assert result == {"name": "John"}

    def test_parse_json_with_surrounding_text(self):
        text = 'Here is the data:\n{"name": "John"}\nEnd of data.'
        result = parse_json_response(text)
        assert result == {"name": "John"}

    def test_parse_invalid_json_returns_none(self):
        assert parse_json_response("not json at all") is None

    def test_parse_empty_string_returns_none(self):
        assert parse_json_response("") is None

    def test_parse_nested_json(self):
        text = '{"student": {"name": "John", "marks": [90, 85]}}'
        result = parse_json_response(text)
        assert result["student"]["marks"] == [90, 85]


class TestExtractDocumentData:
    @patch("modules.ocr_engine.call_lm_studio")
    def test_extract_success(self, mock_call):
        mock_call.return_value = '{"prn": "12345678901", "student_name": "Test Student", "sgpa": 8.5}'
        result = extract_document_data("/fake/path.jpg", "sppu_marksheet")
        assert result["status"] == "success"
        assert result["extracted_fields"]["prn"] == "12345678901"
        assert result["extracted_fields"]["sgpa"] == 8.5

    @patch("modules.ocr_engine.call_lm_studio")
    def test_extract_parse_error(self, mock_call):
        mock_call.return_value = "I cannot read this document clearly"
        result = extract_document_data("/fake/path.jpg", "sppu_marksheet")
        assert result["status"] == "parse_error"
        assert result["extracted_fields"] is None

    @patch("modules.ocr_engine.call_lm_studio")
    def test_extract_lm_studio_error(self, mock_call):
        mock_call.side_effect = ConnectionError("LM Studio not running")
        result = extract_document_data("/fake/path.jpg", "sppu_marksheet")
        assert result["status"] == "error"
        assert "LM Studio" in result["error"]

    def test_extract_invalid_doc_type(self):
        result = extract_document_data("/fake/path.jpg", "invalid_type")
        assert result["status"] == "error"
        assert "No template" in result["error"]


class TestExtractRawText:
    @patch("modules.ocr_engine.call_lm_studio")
    def test_raw_text_success(self, mock_call):
        mock_call.return_value = "SAVITRIBAI PHULE PUNE UNIVERSITY\nSemester Exam Results"
        result = extract_raw_text("/fake/path.jpg")
        assert result["status"] == "success"
        assert "SAVITRIBAI" in result["text"]

    @patch("modules.ocr_engine.call_lm_studio")
    def test_raw_text_error(self, mock_call):
        mock_call.side_effect = ConnectionError("Connection refused")
        result = extract_raw_text("/fake/path.jpg")
        assert result["status"] == "error"
        assert result["text"] is None


# ─── Classifier Tests ────────────────────────────────────────────────


class TestKeywordClassifier:
    def test_classify_sppu_marksheet(self):
        text = "Savitribai Phule Pune University Semester Exam SGPA 8.5 PRN 12345678901"
        result = classify_by_keywords(text)
        assert result["doc_type"] == "sppu_marksheet"
        assert result["confidence"] > 0.5

    def test_classify_aadhaar(self):
        text = "GOVERNMENT OF INDIA AADHAAR Unique Identification Authority 1234 5678 9012"
        result = classify_by_keywords(text)
        assert result["doc_type"] == "aadhaar_card"
        assert result["confidence"] > 0.5

    def test_classify_pan(self):
        text = "INCOME TAX DEPARTMENT PERMANENT ACCOUNT NUMBER ABCDE1234F Govt. of India"
        result = classify_by_keywords(text)
        assert result["doc_type"] == "pan_card"
        assert result["confidence"] > 0.5

    def test_classify_experience_cert(self):
        text = "EXPERIENCE CERTIFICATE This is to hereby certify that Mr. John worked with us Date of Joining"
        result = classify_by_keywords(text)
        assert result["doc_type"] == "experience_certificate"
        assert result["confidence"] > 0.5

    def test_classify_empty_text(self):
        result = classify_by_keywords("")
        assert result["doc_type"] == "unknown"
        assert result["confidence"] == 0.0

    def test_classify_irrelevant_text(self):
        result = classify_by_keywords("Hello world this is a random text about nothing")
        assert result["doc_type"] == "unknown"


class TestClassifyDocument:
    @patch("modules.classifier.classify_by_vision")
    def test_classify_vision_success(self, mock_vision):
        mock_vision.return_value = {
            "doc_type": "pan_card",
            "confidence": 0.85,
            "method": "vision",
        }
        result = classify_document("/fake/path.jpg")
        assert result["doc_type"] == "pan_card"
        assert result["method"] == "vision"

    @patch("modules.classifier.extract_raw_text")
    @patch("modules.classifier.classify_by_vision")
    def test_classify_falls_back_to_keywords(self, mock_vision, mock_text):
        mock_vision.return_value = {
            "doc_type": "unknown",
            "confidence": 0.0,
            "method": "vision",
        }
        mock_text.return_value = {
            "text": "SAVITRIBAI PHULE PUNE UNIVERSITY SGPA PRN",
            "status": "success",
            "error": None,
        }
        result = classify_document("/fake/path.jpg")
        assert result["doc_type"] == "sppu_marksheet"
        assert result["method"] == "keyword"

    @patch("modules.classifier.extract_raw_text")
    @patch("modules.classifier.classify_by_vision")
    def test_classify_both_fail(self, mock_vision, mock_text):
        mock_vision.return_value = {
            "doc_type": "unknown",
            "confidence": 0.0,
            "method": "vision",
        }
        mock_text.return_value = {
            "text": None,
            "status": "error",
            "error": "failed",
        }
        result = classify_document("/fake/path.jpg")
        assert result["doc_type"] == "unknown"


class TestValidDocTypes:
    def test_all_types_present(self):
        assert "sppu_marksheet" in VALID_DOC_TYPES
        assert "aadhaar_card" in VALID_DOC_TYPES
        assert "pan_card" in VALID_DOC_TYPES
        assert "experience_certificate" in VALID_DOC_TYPES


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
