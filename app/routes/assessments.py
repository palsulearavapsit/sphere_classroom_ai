from flask import Blueprint, render_template, request, jsonify, current_app, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from ..services.assessments_service import list_tests, fetch_test, submit_answers, upload_pdf_assessment
from ..services.classrooms_service import list_classrooms_for_teacher, get_classroom_students
from ..services.email_service import email_service
from ..roles import role_required

assess_bp = Blueprint("assessments", __name__, template_folder="../templates")

@assess_bp.route("/", methods=["GET"])
@login_required
def assess_home():
    tests = list_tests(current_user.id)
    classrooms = []
    
    # Get classrooms for teachers to assign assessments
    if current_user.role in ['teacher', 'admin']:
        classrooms = list_classrooms_for_teacher(current_user.id)
    
    return render_template("assessments.html", tests=tests, classrooms=classrooms)

@assess_bp.route("/test/<int:test_id>", methods=["GET"])
@login_required
def assess_detail(test_id):
    test = fetch_test(test_id)
    return render_template("assessment_detail.html", test=test)

@assess_bp.route("/submit/<int:test_id>", methods=["POST"])
@login_required
def assess_submit(test_id):
    payload = request.get_json() or {}
    result = submit_answers(user_id=current_user.id, test_id=test_id, answers=payload.get("answers",[]))
    return jsonify(result)

@assess_bp.route("/pdf/<filename>", methods=["GET"])
@login_required
def serve_pdf(filename):
    """Serve PDF assessment files"""
    try:
        upload_dir = os.path.join(os.getcwd(), 'uploads', 'assessments')
        # Ensure the file exists and is a PDF
        file_path = os.path.join(upload_dir, filename)
        if not os.path.exists(file_path) or not filename.lower().endswith('.pdf'):
            return "PDF file not found", 404
            
        return send_from_directory(upload_dir, filename, mimetype='application/pdf')
    except FileNotFoundError:
        return "PDF file not found", 404
    except Exception as e:
        current_app.logger.error(f"Error serving PDF {filename}: {e}")
        return "Error loading PDF", 500

@assess_bp.route("/upload", methods=["POST"])
@login_required
@role_required("teacher", "admin")
def upload_assessment():
    """Upload PDF assessment - only for teachers"""
    if 'pdf_file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['pdf_file']
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    classroom_id = request.form.get('classroom_id', '').strip()
    
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    if not title:
        return jsonify({"error": "Assessment title is required"}), 400
        
    if not classroom_id:
        return jsonify({"error": "Please select a classroom"}), 400
    
    if file and file.filename.lower().endswith('.pdf'):
        try:
            result = upload_pdf_assessment(file, title, description, current_user.id, classroom_id)
            
            # Send email notifications to all students in the classroom
            if current_app.config.get('SEND_EMAIL_NOTIFICATIONS', True):
                try:
                    from ..services.classrooms_service import get_classroom_by_id
                    from ..db import get_db
                    
                    # Get classroom details
                    classroom = get_classroom_by_id(classroom_id)
                    
                    # Get students in the classroom
                    conn = get_db()
                    students = conn.execute("""
                        SELECT u.id, u.full_name as name, u.email
                        FROM users u
                        JOIN enrollments e ON u.id = e.user_id
                        WHERE e.classroom_id = ? AND u.role = 'student'
                    """, (classroom_id,)).fetchall()
                    
                    students = [dict(student) for student in students]
                    
                    # Prepare assignment data
                    assignment = {
                        'id': result["id"],
                        'title': title,
                        'due_date': 'No due date set'  # Can be enhanced later
                    }
                    
                    teacher = {
                        'name': current_user.name
                    }
                    
                    # Send notifications
                    email_service.notify_assignment_created(assignment, classroom, teacher, students)
                    
                except Exception as email_error:
                    current_app.logger.error(f"Failed to send email notifications: {email_error}")
                    # Don't fail the upload if email fails
            
            return jsonify({"success": True, "assessment_id": result["id"], "message": "Assessment uploaded successfully!"})
        except Exception as e:
            return jsonify({"error": f"Upload failed: {str(e)}"}), 500
    else:
        return jsonify({"error": "Only PDF files are allowed"}), 400
