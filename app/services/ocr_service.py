import io, os, json, uuid
from PIL import Image
try:
    import pytesseract
    # Set Tesseract path for Windows
    if os.name == 'nt':  # Windows
        tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        if os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
except Exception:
    pytesseract = None

# PDF processing imports
try:
    from pdf2image import convert_from_bytes
    import fitz  # PyMuPDF
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("PDF OCR support not available. Install pdf2image and PyMuPDF for PDF support.")

from ..db import get_db
from flask import current_app

def extract_text_from_pdf_ocr(pdf_data: bytes):
    """Extract text from PDF using OCR (for scanned PDFs or images)."""
    if not PDF_SUPPORT or pytesseract is None:
        return "[PDF OCR Error] Missing dependencies. Install pdf2image, PyMuPDF, and Tesseract.", {}
    
    try:
        # Convert PDF pages to images
        images = convert_from_bytes(pdf_data, dpi=200, first_page=1, last_page=10)  # Limit to first 10 pages
        
        all_text = []
        all_lines = []
        
        for page_num, image in enumerate(images, 1):
            try:
                # OCR each page
                page_text = pytesseract.image_to_string(image)
                if page_text.strip():
                    all_text.append(f"[Page {page_num}]\n{page_text}")
                    page_lines = [line.strip() for line in page_text.splitlines() if line.strip()]
                    all_lines.extend([f"Page {page_num}: {line}" for line in page_lines])
            except Exception as e:
                all_text.append(f"[Page {page_num} OCR Error] {str(e)}")
        
        combined_text = "\n\n".join(all_text)
        struct = {
            "pages": len(images),
            "lines": all_lines,
            "method": "OCR"
        }
        
        return combined_text, struct
        
    except Exception as e:
        return f"[PDF OCR Error] {str(e)}", {"error": str(e)}

def extract_text_from_pdf_direct(pdf_data: bytes):
    """Extract text directly from PDF (for text-based PDFs)."""
    if not PDF_SUPPORT:
        return "[PDF Error] Missing PyMuPDF dependency.", {}
    
    doc = None
    try:
        # Open PDF with PyMuPDF
        doc = fitz.open(stream=pdf_data, filetype="pdf")
        
        all_text = []
        all_lines = []
        
        for page_num in range(min(len(doc), 10)):  # Limit to first 10 pages
            page = doc[page_num]
            page_text = page.get_text()
            
            if page_text.strip():
                all_text.append(f"[Page {page_num + 1}]\n{page_text}")
                page_lines = [line.strip() for line in page_text.splitlines() if line.strip()]
                all_lines.extend([f"Page {page_num + 1}: {line}" for line in page_lines])
        
        # Store page count before closing document
        page_count = len(doc)
        
        combined_text = "\n\n".join(all_text)
        struct = {
            "pages": page_count,
            "lines": all_lines,
            "method": "Direct Text Extraction"
        }
        
        return combined_text, struct
        
    except Exception as e:
        return f"[PDF Direct Extraction Error] {str(e)}", {"error": str(e)}
    finally:
        # Ensure document is always closed
        if doc is not None:
            try:
                doc.close()
            except:
                pass  # Ignore errors when closing

def extract_text_from_pdf(pdf_data: bytes):
    """Extract text from PDF using the best available method."""
    # First try direct text extraction (faster for text-based PDFs)
    text, struct = extract_text_from_pdf_direct(pdf_data)
    
    # If direct extraction didn't get much text, try OCR
    if len(text.strip()) < 100 and not text.startswith("[PDF"):
        ocr_text, ocr_struct = extract_text_from_pdf_ocr(pdf_data)
        if len(ocr_text.strip()) > len(text.strip()):
            text = ocr_text
            struct = ocr_struct
            struct["fallback_to_ocr"] = True
    
    return text, struct

def extract_text(user_id, filename, data: bytes):
    # Save to uploads
    uid = str(uuid.uuid4())
    save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], f"{uid}_{filename}")
    with open(save_path, "wb") as f:
        f.write(data)

    text = ""
    struct = {}
    
    # Determine file type
    file_ext = os.path.splitext(filename.lower())[1]
    
    if file_ext == '.pdf':
        # Handle PDF files
        if not PDF_SUPPORT:
            text = "[PDF OCR Error] PDF support not available. Install pdf2image and PyMuPDF."
            struct = {"error": "Missing PDF dependencies"}
        else:
            text, struct = extract_text_from_pdf(data)
            struct["file_type"] = "PDF"
    else:
        # Handle image files
        if pytesseract is None:
            text = "[OCR disabled] Install Tesseract+pytesseract to enable extraction."
            struct = {"error": "Missing Tesseract"}
        else:
            try:
                img = Image.open(io.BytesIO(data)).convert("RGB")
                text = pytesseract.image_to_string(img)
                # naive structure: lines list
                struct = {
                    "lines": [line for line in text.splitlines() if line.strip()],
                    "file_type": "Image"
                }
            except Exception as e:
                text = f"[OCR Error] Failed to process image. Error: {str(e)}\n\nSupported formats: JPG, PNG, GIF, BMP, PDF\n\nFor PDF files, ensure pdf2image and PyMuPDF are installed."
                struct = {"error": str(e), "file_type": "Image"}

    # Store in database
    db = get_db()
    db.execute(
        "INSERT INTO ocr_extractions(user_id,image_path,text,struct_json) VALUES(?,?,?,?)",
        (user_id, save_path, text, json.dumps(struct))
    )
    db.commit()
    return text, struct
