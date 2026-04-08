import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
ML_MODELS_DIR = BASE_DIR / "ml_models"
TEMPLATES_DIR = BASE_DIR / "templates"

# Ensure directories exist
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Database
DATABASE_URL = f"sqlite:///{BASE_DIR / 'verification.db'}"

# LM Studio (local LLM server)
LM_STUDIO_BASE_URL = "http://localhost:1234/v1"
LM_STUDIO_API_KEY = "lm-studio"

# OCR settings
TESSERACT_CONFIDENCE_THRESHOLD = 70  # below this, use LLM fallback

# Preprocessing settings
TARGET_DPI = 300
MAX_IMAGE_DIMENSION = 4000  # max width or height in pixels

# Supported file types
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf", ".heic"}
MAX_FILE_SIZE_MB = 20
