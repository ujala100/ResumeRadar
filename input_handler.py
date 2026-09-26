"""
Accepts resume input as: plain text, a text-based PDF, or a scanned/image
PDF (falls back to OCR). This directly addresses the "scanned/image-heavy
PDF resume" adversarial test case from the brief.
"""

import os


def load_resume_text(path_or_text: str) -> str:
    """
    If given a path to a .pdf, extract text (with OCR fallback).
    If given a path to a .txt, read it.
    Otherwise, treat the input as raw text directly.
    """
    if os.path.isfile(path_or_text):
        if path_or_text.lower().endswith(".pdf"):
            return _extract_pdf_text(path_or_text)
        elif path_or_text.lower().endswith(".txt"):
            with open(path_or_text, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
    return path_or_text  # assume raw text was passed directly


def _extract_pdf_text(pdf_path: str) -> str:
    import pdfplumber

    text_chunks = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_chunks.append(page_text)

    combined = "\n".join(text_chunks).strip()

    # If almost no text was extracted, it's likely a scanned/image PDF -> OCR fallback
    if len(combined) < 30:
        combined = _ocr_pdf(pdf_path)

    return combined


def _ocr_pdf(pdf_path: str) -> str:
    """OCR fallback for scanned/image-based PDFs."""
    try:
        from pdf2image import convert_from_path
        import pytesseract

        pages = convert_from_path(pdf_path)
        text_chunks = [pytesseract.image_to_string(page) for page in pages]
        return "\n".join(text_chunks).strip()
    except Exception as e:
        return f"[OCR_FAILED: {e}]"
