from io import BytesIO
from PIL import Image, ImageFilter
import pytesseract

def ocr_image_bytes(image_bytes: bytes, preprocess: bool = True) -> str:
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    if preprocess:
        img = img.filter(ImageFilter.MedianFilter(3))
    try:
        text = pytesseract.image_to_string(img)
        return text.strip()
    except Exception as e:
        return f"OCR Error: {e}"
