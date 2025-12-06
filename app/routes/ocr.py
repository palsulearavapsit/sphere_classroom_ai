import io, os
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from ..services.ocr_service import extract_text
from ..services.ocr_data_service import get_user_ocr_extractions, search_ocr_text

ocr_bp = Blueprint("ocr", __name__, template_folder="../templates")

@ocr_bp.route("/", methods=["GET"])
@login_required
def ocr_home():
    return render_template("ocr.html")

@ocr_bp.route("/upload", methods=["POST"])
@login_required
def ocr_upload():
    if "image" not in request.files:
        return jsonify({"error":"no file"}), 400
    
    f = request.files["image"]
    if not f.filename:
        return jsonify({"error": "No file selected"}), 400
    
    # Check file extension
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.pdf'}
    file_ext = os.path.splitext(f.filename.lower())[1]
    
    if file_ext not in allowed_extensions:
        return jsonify({
            "error": f"Unsupported file type: {file_ext}. Supported: {', '.join(allowed_extensions)}"
        }), 400
    
    try:
        data = f.read()
        text, struct = extract_text(current_user.id, f.filename, data)
        
        # Add file type info to response
        response_data = {
            "text": text, 
            "struct": struct,
            "filename": f.filename,
            "file_type": struct.get("file_type", "Unknown")
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({"error": f"Processing failed: {str(e)}"}), 500

@ocr_bp.route("/extractions", methods=["GET"])
@login_required
def view_extractions():
    """View all OCR extractions for the current user."""
    extractions = get_user_ocr_extractions(current_user.id, limit=50)
    return render_template("ocr_extractions.html", extractions=extractions)

@ocr_bp.route("/search", methods=["GET"])
@login_required
def search_extractions():
    """Search OCR extractions."""
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "No search query provided"}), 400
    
    results = search_ocr_text(current_user.id, query, limit=20)
    return jsonify({"results": results, "query": query})
