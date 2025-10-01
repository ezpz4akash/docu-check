# backend/ocr/tesseract.py
import os
from typing import List, Tuple

try:
    from PIL import Image
    import pytesseract
except Exception as e:
    raise RuntimeError("Pillow and pytesseract must be installed. pip install pillow pytesseract") from e

def _extract_text_from_image(path: str) -> str:
    img = Image.open(path)
    # convert to RGB to avoid palette issues
    if img.mode != "RGB":
        img = img.convert("RGB")
    txt = pytesseract.image_to_string(img)
    return txt

def extract_text_from_path(path: str) -> List[Tuple[str, str]]:
    """
    Returns a list of tuples: (source_filename, extracted_text).
    For single-image/pdf it returns one tuple. If the input is a PDF with multiple pages
    this function will attempt to split pages if poppler is available (pdf2image).
    """
    path = os.path.abspath(path)
    lower = path.lower()
    if lower.endswith(".pdf"):
        # try to import pdf2image (requires poppler)
        try:
            from pdf2image import convert_from_path
        except Exception:
            raise RuntimeError("pdf2image/poppler not available. Install poppler or convert PDFs to images.")
        images = convert_from_path(path, dpi=200)
        out = []
        for i, img in enumerate(images):
            txt = pytesseract.image_to_string(img)
            out.append((f"{os.path.basename(path)}:page:{i+1}", txt))
        return out
    else:
        # assume image
        txt = _extract_text_from_image(path)
        return [(os.path.basename(path), txt)]
