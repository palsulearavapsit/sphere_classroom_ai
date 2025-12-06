from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
import os
from ..roles import role_required
from ..services.rag_service import ingest_document, reindex_all, semantic_search, indexing_status

rag_bp = Blueprint("rag", __name__, template_folder="../templates")

@rag_bp.route("/", methods=["GET"])
@login_required
def rag_home():
    status = indexing_status()
    return render_template("admin_rag.html", status=status)

@rag_bp.route("/ingest", methods=["POST"])
@login_required
def rag_ingest():
    f = request.files.get("file")
    namespace = request.form.get("namespace","default")
    if not f:
        return jsonify({"error":"no file"}), 400
    
    # Check file extension
    allowed_extensions = {'.pdf', '.doc', '.docx', '.txt', '.md'}
    file_ext = os.path.splitext(f.filename.lower())[1]
    if file_ext not in allowed_extensions:
        return jsonify({"error": f"Unsupported file type: {file_ext}. Supported: {', '.join(allowed_extensions)}"}), 400
    
    try:
        ok = ingest_document(f.filename, f.read(), namespace)
        if ok:
            return jsonify({"ok": True, "message": f"Successfully processed {f.filename}", "filename": f.filename})
        else:
            return jsonify({"error": "Failed to process document"}), 500
    except Exception as e:
        return jsonify({"error": f"Error processing document: {str(e)}"}), 500

@rag_bp.route("/reindex", methods=["POST"])
@login_required
@role_required("teacher","admin")
def rag_reindex():
    return jsonify(reindex_all())

@rag_bp.route("/search", methods=["POST"])
@login_required
def rag_search():
    q = (request.get_json() or {}).get("q","").strip()
    namespace = (request.get_json() or {}).get("namespace","default")
    return jsonify(semantic_search(q, namespace))
