"""
ocr_utils.py — ScanLens OCR Pipeline
=======================================
Handles text extraction from:
  - Images (JPG, PNG, WebP) — especially WhatsApp screenshots
  - PDF files (text-based and scanned/image PDFs)

Cross-platform: works on Windows, Linux (Streamlit Cloud), and macOS.
Tesseract path is auto-detected — no hardcoded paths needed.
"""

import re
import io
import shutil
from typing import Optional

# ------------------------------------------------------------------ #
#  SAFE IMPORTS (graceful degradation if libraries not installed)
# ------------------------------------------------------------------ #

try:
    from PIL import Image, ImageFilter, ImageEnhance, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import pytesseract
    # Auto-detect Tesseract binary — works on Linux/Cloud AND Windows
    _tess_path = shutil.which("tesseract")
    if _tess_path:
        pytesseract.pytesseract.tesseract_cmd = _tess_path
    # On Windows, fall back to default install path only if not found in PATH
    else:
        import platform
        if platform.system() == "Windows":
            import os
            win_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            if os.path.exists(win_path):
                pytesseract.pytesseract.tesseract_cmd = win_path
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    from pdf2image import convert_from_bytes
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False


# ------------------------------------------------------------------ #
#  IMAGE PREPROCESSING
# ------------------------------------------------------------------ #

def _preprocess_image(img) -> "Image":
    """
    Multi-step preprocessing optimised for WhatsApp screenshots and
    noisy mobile screenshots.
    """
    img = img.convert("L")
    w, h = img.size
    if w < 1200:
        scale = 1200 / w
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    img = ImageEnhance.Contrast(img).enhance(2.0)
    img = ImageEnhance.Sharpness(img).enhance(2.0)
    img = img.filter(ImageFilter.MedianFilter(size=3))
    img = img.point(lambda p: 255 if p > 150 else 0)
    return img


def _clean_ocr_output(text: str) -> str:
    """Post-process raw Tesseract output."""
    if not text:
        return ""
    lines = text.splitlines()
    clean_lines = []
    for line in lines:
        line = line.strip()
        if len(line) <= 2 and not line.isdigit():
            continue
        clean_lines.append(line)
    text = "\n".join(clean_lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[^\x20-\x7E\n₹]", "", text)
    return text.strip()


# ------------------------------------------------------------------ #
#  IMAGE OCR
# ------------------------------------------------------------------ #

def extract_text_from_image(image_file) -> str:
    """
    Extract text from an uploaded image file.
    """
    if not PIL_AVAILABLE:
        return "[Error] Pillow is not installed. Run: pip install Pillow"
    if not TESSERACT_AVAILABLE:
        return "[Error] pytesseract is not installed. Run: pip install pytesseract"

    try:
        img = Image.open(image_file)
        img = _preprocess_image(img)
        config = "--oem 3 --psm 6 -l eng"
        raw_text = pytesseract.image_to_string(img, config=config)
        return _clean_ocr_output(raw_text)
    except Exception as e:
        return f"[OCR Error] Could not process image: {str(e)}"


def extract_text_from_image_bytes(image_bytes: bytes, fmt: str = "PNG") -> str:
    """Convenience wrapper — accepts raw bytes instead of file object."""
    if not PIL_AVAILABLE:
        return "[Error] Pillow not available."
    buf = io.BytesIO(image_bytes)
    return extract_text_from_image(buf)


# ------------------------------------------------------------------ #
#  PDF OCR
# ------------------------------------------------------------------ #

def extract_text_from_pdf(pdf_file) -> str:
    """
    Extract text from a PDF.
    Strategy:
    1. Try pdfplumber first (fast, accurate for text-based PDFs)
    2. Fall back to pdf2image + Tesseract OCR for scanned PDFs
    """
    extracted = ""

    if PDFPLUMBER_AVAILABLE:
        try:
            with pdfplumber.open(pdf_file) as pdf:
                pages_text = []
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        pages_text.append(t)
                extracted = "\n\n".join(pages_text)
        except Exception:
            extracted = ""

    if len(extracted.strip()) < 50:
        if PDF2IMAGE_AVAILABLE and PIL_AVAILABLE and TESSERACT_AVAILABLE:
            try:
                if hasattr(pdf_file, "read"):
                    pdf_bytes = pdf_file.read()
                    pdf_file.seek(0)
                else:
                    with open(pdf_file, "rb") as f:
                        pdf_bytes = f.read()
                images = convert_from_bytes(pdf_bytes, dpi=200)
                pages_text = []
                for img in images:
                    img_processed = _preprocess_image(img)
                    raw = pytesseract.image_to_string(img_processed, config="--oem 3 --psm 6")
                    pages_text.append(_clean_ocr_output(raw))
                extracted = "\n\n".join(pages_text)
            except Exception as e:
                extracted = f"[OCR Fallback Error] {str(e)}"
        elif not PDFPLUMBER_AVAILABLE:
            extracted = "[Error] pdfplumber not installed. Run: pip install pdfplumber"

    return _clean_ocr_output(extracted) if extracted else "[No text could be extracted from this PDF.]"


# ------------------------------------------------------------------ #
#  UNIFIED ENTRY POINT
# ------------------------------------------------------------------ #

def extract_text(uploaded_file) -> str:
    """
    Auto-detect file type and route to the correct extractor.
    Designed for use with Streamlit's st.file_uploader().
    """
    if uploaded_file is None:
        return ""
    file_name = uploaded_file.name.lower()
    if file_name.endswith(".pdf"):
        return extract_text_from_pdf(uploaded_file)
    elif any(file_name.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"]):
        return extract_text_from_image(uploaded_file)
    else:
        return "[Unsupported file type. Please upload PNG, JPG, WEBP, or PDF.]"


# ------------------------------------------------------------------ #
#  DEPENDENCY CHECKER
# ------------------------------------------------------------------ #

def ocr_status() -> dict:
    """Returns a status dict showing which OCR components are available."""
    return {
        "Pillow":      PIL_AVAILABLE,
        "pytesseract": TESSERACT_AVAILABLE,
        "pdfplumber":  PDFPLUMBER_AVAILABLE,
        "pdf2image":   PDF2IMAGE_AVAILABLE,
        "image_ocr":   PIL_AVAILABLE and TESSERACT_AVAILABLE,
        "pdf_text":    PDFPLUMBER_AVAILABLE,
        "pdf_ocr":     PDF2IMAGE_AVAILABLE and TESSERACT_AVAILABLE,
    }
