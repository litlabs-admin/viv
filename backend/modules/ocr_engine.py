"""
OCR Engine - LM Studio Vision-based Document Text Extraction

Uses LM Studio's local LLaVA model to extract structured data
from document images. No Tesseract dependency.
"""

import base64
import json
import re
from pathlib import Path
from typing import Optional

from openai import OpenAI

from config import (
    LM_STUDIO_BASE_URL,
    LM_STUDIO_API_KEY,
    LM_STUDIO_MODEL,
    LM_STUDIO_TEMPERATURE,
    LM_STUDIO_MAX_TOKENS,
    TEMPLATES_DIR,
)


def get_lm_client():
    """Create an OpenAI client pointing to LM Studio's local server."""
    return OpenAI(base_url=LM_STUDIO_BASE_URL, api_key=LM_STUDIO_API_KEY)


def image_to_base64(image_path: str) -> str:
    """Read an image file and return its base64 encoding."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_image_mime_type(image_path: str) -> str:
    """Determine MIME type from file extension."""
    ext = Path(image_path).suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    return mime_map.get(ext, "image/jpeg")


def load_template(doc_type: str) -> Optional[dict]:
    """Load the JSON template for a given document type."""
    template_map = {
        "sppu_marksheet": "sppu_marksheet_template.json",
        "aadhaar_card": "aadhaar_template.json",
        "pan_card": "pan_template.json",
        "experience_certificate": "experience_cert_template.json",
    }
    filename = template_map.get(doc_type)
    if not filename:
        return None
    template_path = TEMPLATES_DIR / filename
    if not template_path.exists():
        return None
    with open(template_path, "r") as f:
        return json.load(f)


def build_extraction_prompt(doc_type: str, template: dict) -> str:
    """Build a structured prompt for field extraction based on document type."""
    fields = template.get("fields", {})
    field_descriptions = []
    for field_name, field_info in fields.items():
        if isinstance(field_info, dict) and field_info.get("type") == "array":
            # Handle array fields like subjects
            items = field_info.get("items", {})
            item_fields = ", ".join(items.keys())
            field_descriptions.append(
                f'- "{field_name}": array of objects with fields: {item_fields}'
            )
        else:
            required = ""
            if isinstance(field_info, dict) and field_info.get("required"):
                required = " (REQUIRED)"
            field_descriptions.append(f'- "{field_name}"{required}')

    fields_text = "\n".join(field_descriptions)
    doc_name = template.get("description", doc_type)

    return f"""You are a precise document data extractor. You are looking at an image of a {doc_name}.

Extract ALL the following fields from this document image:
{fields_text}

IMPORTANT RULES:
1. Return ONLY valid JSON, no other text before or after.
2. Use null for fields you cannot read or find.
3. For numeric values (marks, SGPA, etc.), return them as numbers, not strings.
4. For arrays (like subjects), include ALL items visible in the document.
5. Read carefully - accuracy is critical. Double-check numbers and names.
6. If the image is unclear, extract what you can and use null for unreadable fields."""


def build_raw_text_prompt() -> str:
    """Build a prompt for raw text extraction (used for classification/NLP)."""
    return """Read this document image and extract ALL visible text exactly as it appears.
Include headers, labels, values, numbers, stamps, and any other text.
Preserve the general layout/structure using newlines.
Return ONLY the extracted text, nothing else."""


def parse_json_response(response_text: str) -> Optional[dict]:
    """Parse JSON from LLM response, handling common formatting issues."""
    text = response_text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON from markdown code blocks
    json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try finding JSON object in text
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def call_lm_studio(image_path: str, prompt: str) -> str:
    """Send an image + prompt to LM Studio and return the response text."""
    client = get_lm_client()
    b64_image = image_to_base64(image_path)
    mime_type = get_image_mime_type(image_path)

    response = client.chat.completions.create(
        model=LM_STUDIO_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{b64_image}"
                        },
                    },
                ],
            }
        ],
        temperature=LM_STUDIO_TEMPERATURE,
        max_tokens=LM_STUDIO_MAX_TOKENS,
    )
    return response.choices[0].message.content


def extract_document_data(image_path: str, doc_type: str) -> dict:
    """
    Extract structured data from a document image using LM Studio vision.

    Args:
        image_path: Path to the document image file.
        doc_type: One of 'sppu_marksheet', 'aadhaar_card', 'pan_card', 'experience_certificate'.

    Returns:
        Dict with keys:
            - extracted_fields: dict of extracted field values (or None on failure)
            - raw_response: raw LLM response text
            - doc_type: the document type used
            - status: 'success' or 'error'
            - error: error message if status is 'error'
    """
    template = load_template(doc_type)
    if not template:
        return {
            "extracted_fields": None,
            "raw_response": None,
            "doc_type": doc_type,
            "status": "error",
            "error": f"No template found for document type: {doc_type}",
        }

    prompt = build_extraction_prompt(doc_type, template)

    try:
        raw_response = call_lm_studio(image_path, prompt)
    except Exception as e:
        return {
            "extracted_fields": None,
            "raw_response": None,
            "doc_type": doc_type,
            "status": "error",
            "error": f"LM Studio call failed: {str(e)}",
        }

    extracted = parse_json_response(raw_response)

    return {
        "extracted_fields": extracted,
        "raw_response": raw_response,
        "doc_type": doc_type,
        "status": "success" if extracted else "parse_error",
        "error": "Could not parse JSON from LLM response" if not extracted else None,
    }


def extract_raw_text(image_path: str) -> dict:
    """
    Extract raw text from a document image using LM Studio vision.

    Args:
        image_path: Path to the document image file.

    Returns:
        Dict with keys:
            - text: extracted text string (or None on failure)
            - status: 'success' or 'error'
            - error: error message if status is 'error'
    """
    prompt = build_raw_text_prompt()

    try:
        raw_text = call_lm_studio(image_path, prompt)
        return {
            "text": raw_text.strip(),
            "status": "success",
            "error": None,
        }
    except Exception as e:
        return {
            "text": None,
            "status": "error",
            "error": f"LM Studio call failed: {str(e)}",
        }
