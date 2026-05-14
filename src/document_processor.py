from __future__ import annotations

import io
import shutil
from pathlib import Path
from typing import Dict, Tuple

try:
    import fitz
except Exception:  # pragma: no cover - handled at runtime
    fitz = None

try:
    from PIL import Image
except Exception:  # pragma: no cover - handled at runtime
    Image = None

try:
    import pytesseract
except Exception:  # pragma: no cover - handled at runtime
    pytesseract = None


SUPPORTED_TEXT_EXTENSIONS = {".pdf", ".txt"}
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def tesseract_available() -> bool:
    if pytesseract is None:
        return False
    executable = shutil.which("tesseract")
    if executable is None:
        return False
    try:
        _ = pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def extract_pdf_text(file_bytes: bytes):
    debug = {}
    text_pages = []

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        debug["pdf_page_count"] = len(doc)

        for i, page in enumerate(doc):
            page_text = page.get_text("text") or ""
            debug[f"page_{i+1}_chars"] = len(page_text)
            text_pages.append(page_text)

        doc.close()
        text = "\n".join(text_pages).strip()
        debug["pymupdf_chars"] = len(text)
        return text, debug

    except Exception as e:
        debug["pdf_error"] = str(e)
        debug["pdf_page_count"] = 0
        debug["pymupdf_chars"] = 0
        return "", debug


def extract_pdf_ocr_text(file_bytes: bytes) -> Tuple[str, bool]:
    if fitz is None or not tesseract_available() or Image is None:
        return "", False

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception:
        return "", False

    ocr_pages = []
    used_ocr = False

    try:
        for page in doc:
            try:
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                image = Image.open(io.BytesIO(pix.tobytes("png")))
                page_text = pytesseract.image_to_string(image) if pytesseract is not None else ""
            except Exception:
                page_text = ""
            if page_text and page_text.strip():
                used_ocr = True
            ocr_pages.append(page_text or "")
    finally:
        doc.close()

    return "\n".join(ocr_pages).strip(), used_ocr


def extract_text_from_image(file_bytes: bytes) -> Tuple[str, bool]:
    if not tesseract_available() or Image is None:
        return "", True
    try:
        image = Image.open(io.BytesIO(file_bytes))
        text = pytesseract.image_to_string(image)
    except Exception:
        return "", True
    return text, True


def extract_text_from_txt(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8", errors="ignore")


def process_uploaded_file(file_bytes: bytes, file_name: str, extracted_dir: Path) -> Dict[str, str]:
    ensure_directory(extracted_dir)
    suffix = Path(file_name).suffix.lower()

    extracted_text = ""
    warning = ""
    ocr_warning = ""
    pdf_debug = {}

    if suffix == ".pdf":
        extracted_text, pdf_debug = extract_pdf_text(file_bytes)
        if pdf_debug.get("pdf_error"):
            warning = pdf_debug["pdf_error"]
        elif pdf_debug.get("pdf_page_count", 0) == 0:
            warning = "PyMuPDF opened the file but found 0 pages."
        elif not extracted_text.strip():
            ocr_text, ocr_used = extract_pdf_ocr_text(file_bytes)
            if ocr_used:
                extracted_text = ocr_text
                ocr_warning = "OCR fallback was used for the PDF."
            else:
                ocr_warning = "OCR fallback unavailable. Please install Tesseract OCR."
    elif suffix in SUPPORTED_IMAGE_EXTENSIONS:
        if tesseract_available():
            extracted_text, _ = extract_text_from_image(file_bytes)
            ocr_warning = "OCR fallback was used for the image file."
        else:
            warning = "Tesseract is not installed or not on PATH, so image OCR is unavailable."
    elif suffix == ".txt":
        try:
            extracted_text = extract_text_from_txt(file_bytes)
        except Exception:
            warning = "The text file could not be decoded."
    else:
        warning = f"Unsupported file type: {suffix}"

    safe_name = Path(Path(file_name).name).stem
    extracted_path = extracted_dir / f"{safe_name}.txt"
    try:
        extracted_path.write_text(extracted_text, encoding="utf-8")
    except Exception:
        # fallback: write to a timestamped filename
        safe_path = extracted_dir / f"extracted_{int(Path().stat().st_mtime)}.txt"
        safe_path.write_text(extracted_text, encoding="utf-8")
        extracted_path = safe_path

    result = {
        "document_name": file_name,
        "file_ext": suffix,
        "file_size": len(file_bytes) if isinstance(file_bytes, (bytes, bytearray)) else 0,
        "extracted_text": extracted_text,
        "extracted_path": str(extracted_path),
        "extracted_char_count": len(extracted_text or ""),
        "warning": warning,
        "ocr_warning": ocr_warning,
        "pdf_error": pdf_debug.get("pdf_error", ""),
        "pdf_page_count": pdf_debug.get("pdf_page_count", 0),
        "pymupdf_chars": pdf_debug.get("pymupdf_chars", len(extracted_text or "")),
    }

    return result