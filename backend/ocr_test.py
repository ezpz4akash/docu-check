import pytesseract

# Example for Windows (adjust path if different)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

text = pytesseract.image_to_string("samples/w2_sample.jpg")
print(text)
