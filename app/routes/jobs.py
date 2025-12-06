"""
Job Management Routes
API endpoints for background job monitoring and control
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required
from ..roles import role_required
from ..services.job_service import queue_job, get_job_status, get_queue_info
from ..services.job_service import process_ocr_async, process_rag_reindex_async, generate_assessment_async

jobs_bp = Blueprint("jobs", __name__)

@jobs_bp.route("/status/<job_id>", methods=["GET"])
@login_required
def job_status(job_id):
    """Get status of a specific job"""
    status = get_job_status(job_id)
    return jsonify(status)

@jobs_bp.route("/queue/info", methods=["GET"])
@login_required
@role_required("admin")
def queue_info():
    """Get queue information (admin only)"""
    info = get_queue_info()
    return jsonify(info)

@jobs_bp.route("/ocr/async", methods=["POST"])
@login_required
def queue_ocr():
    """Queue OCR processing job"""
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    # Read file data
    image_data = file.read()
    filename = file.filename
    
    # Queue the job
    result = queue_job(process_ocr_async, image_data, filename)
    return jsonify(result)

@jobs_bp.route("/rag/reindex/async", methods=["POST"])
@login_required
@role_required("teacher", "admin")
def queue_rag_reindex():
    """Queue RAG reindexing job"""
    result = queue_job(process_rag_reindex_async)
    return jsonify(result)

@jobs_bp.route("/assessment/generate/async", methods=["POST"])
@login_required
@role_required("teacher", "admin")
def queue_assessment_generation():
    """Queue assessment generation job"""
    data = request.get_json() or {}
    topic = data.get("topic", "").strip()
    level = data.get("level", "medium")
    
    if not topic:
        return jsonify({"error": "Topic is required"}), 400
    
    result = queue_job(generate_assessment_async, topic, level)
    return jsonify(result)