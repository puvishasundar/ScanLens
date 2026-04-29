"""
ocr_utils.py — ScanLens OCR Pipeline
=======================================
Handles text extraction from:
  - Images (JPG, PNG, WebP) — especially WhatsApp screenshots
  - PDF files (text-based and scanned/image PDFs)

Dependencies (install via pip):
  - Pillow
  - pytesseract   (+ Tesseract binary)
  - pdfplumber    (text-based PDFs)
  - pdf2image     (fallback for scanned PDFs — needs poppler)

Usage in app.py (optional integration):
    from ocr_utils import extract_text_from_image, extract_text_from_pdf
"""
import pytesseract
import re
import io
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

    Steps:
    1. Convert to grayscale
    2. Resize to minimum 1200px width (Tesseract prefers larger images)
    3. Enhance contrast and sharpness
    4. Apply median filter to reduce noise
    5. Binarise (Otsu-like threshold)
    """
    # Step 1: grayscale
    img = img.convert("L")

    # Step 2: upscale small images
    w, h = img.size
    if w < 1200:
        scale = 1200 / w
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    # Step 3: contrast + sharpness boost
    img = ImageEnhance.Contrast(img).enhance(2.0)
    img = ImageEnhance.Sharpness(img).enhance(2.0)

    # Step 4: median filter (remove noise)
    img = img.filter(ImageFilter.MedianFilter(size=3))

    # Step 5: binarise — threshold at 150/255
    img = img.point(lambda p: 255 if p > 150 else 0)

    return img


def _clean_ocr_output(text: str) -> str:
    """
    Post-process raw Tesseract output:
    - Remove isolated single characters on a line
    - Collapse multiple blank lines
    - Strip leading/trailing whitespace
    - Fix common OCR ligature issues
    """
    if not text:
        return ""

    # Common OCR substitution fixes
    fixes = {
        "0": "o",   # only in alpha contexts — skip numeric
        "|": "I",
        "l": "l",   # already l, but some fonts confuse 1 and l
    }

    lines = text.splitlines()
    clean_lines = []
    for line in lines:
        line = line.strip()
        # Drop lines that are just 1–2 random characters (OCR noise)
        if len(line) <= 2 and not line.isdigit():
            continue
        clean_lines.append(line)

    text = "\n".join(clean_lines)
    # Collapse 3+ blank lines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove non-printable characters
    text = re.sub(r"[^\x20-\x7E\n₹]", "", text)
    return text.strip()


# ------------------------------------------------------------------ #
#  IMAGE OCR
# ------------------------------------------------------------------ #

def extract_text_from_image(image_file) -> str:
    """
    Extract text from an uploaded image file.

    Parameters
    ----------
    image_file : file-like object or path string
        Streamlit UploadedFile, BytesIO, or path to image.

    Returns
    -------
    str — extracted and cleaned text, or error message.
    """
    if not PIL_AVAILABLE:
        return "[Error] Pillow is not installed. Run: pip install Pillow"
    if not TESSERACT_AVAILABLE:
        return "[Error] pytesseract is not installed. Run: pip install pytesseract"

    try:
        img = Image.open(image_file)
        img = _preprocess_image(img)

        # Tesseract config: OEM 3 (LSTM), PSM 6 (uniform block of text)
        # Works well for WhatsApp chat screenshots
        config = "--oem 3 --psm 6 -l eng"
        raw_text = pytesseract.image_to_string(img, config=config)
        return _clean_ocr_output(raw_text)

    except Exception as e:
        return f"[OCR Error] Could not process image: {str(e)}"


def extract_text_from_image_bytes(image_bytes: bytes, fmt: str = "PNG") -> str:
    """
    Convenience wrapper — accepts raw bytes instead of file object.
    """
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
    2. If extracted text is too short (<50 chars), fall back to
       pdf2image + Tesseract OCR (for scanned/image PDFs)

    Parameters
    ----------
    pdf_file : file-like object or path string

    Returns
    -------
    str — extracted text.
    """
    extracted = ""

    # --- Pass 1: pdfplumber ---
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

    # --- Pass 2: OCR fallback ---
    if len(extracted.strip()) < 50:
        if PDF2IMAGE_AVAILABLE and PIL_AVAILABLE and TESSERACT_AVAILABLE:
            try:
                # Read bytes (handle both file path and file object)
                if hasattr(pdf_file, "read"):
                    pdf_bytes = pdf_file.read()
                    pdf_file.seek(0)   # rewind for any re-use
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

    Supported types: png, jpg, jpeg, webp, pdf

    Example usage in app.py:
        uploaded = st.file_uploader("Upload image or PDF", type=["png","jpg","jpeg","webp","pdf"])
        if uploaded:
            text = extract_text(uploaded)
            # pass text to predict_risk()
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
#  DEPENDENCY CHECKER (call at startup for user feedback)
# ------------------------------------------------------------------ #

def ocr_status() -> dict:
    """
    Returns a status dict showing which OCR components are available.
    Can be displayed in app.py's sidebar for transparency.
    """
    return {
        "Pillow":      PIL_AVAILABLE,
        "pytesseract": TESSERACT_AVAILABLE,
        "pdfplumber":  PDFPLUMBER_AVAILABLE,
        "pdf2image":   PDF2IMAGE_AVAILABLE,
        "image_ocr":   PIL_AVAILABLE and TESSERACT_AVAILABLE,
        "pdf_text":    PDFPLUMBER_AVAILABLE,
        "pdf_ocr":     PDF2IMAGE_AVAILABLE and TESSERACT_AVAILABLE,
    }
