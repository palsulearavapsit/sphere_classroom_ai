from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from ..roles import role_required
from ..services.classrooms_service import (
    create_classroom, delete_classroom, enroll_with_code, list_enrolled,
    get_classroom_detail, get_classroom_students, get_classroom_assignments
)
from ..services.email_service import email_service

class_bp = Blueprint("classrooms", __name__, template_folder="../templates")

@class_bp.route("/", methods=["GET"])
@login_required
def rooms_home():
    classes = list_enrolled(current_user.id)
    return render_template("classrooms.html", classes=classes)

@class_bp.route("/create", methods=["POST"])
@login_required
@role_required("teacher","admin")
def rooms_create():
    name = (request.get_json() or {}).get("name","").strip()
    room = create_classroom(name, current_user.id)
    return jsonify(room)

@class_bp.route("/delete", methods=["POST"])
@login_required
@role_required("teacher","admin")
def rooms_delete():
    cid = (request.get_json() or {}).get("id")
    ok = delete_classroom(cid, current_user.id)
    return jsonify({"ok": ok})

@class_bp.route("/join", methods=["POST"])
@login_required
def rooms_join():
    code = (request.get_json() or {}).get("code","").strip()
    ok = enroll_with_code(current_user.id, code)
    
    # Send email notifications on successful enrollment
    if ok and current_app.config.get('SEND_EMAIL_NOTIFICATIONS', True):
        try:
            from ..db import get_db
            
            # Get classroom and teacher details
            conn = get_db()
            classroom_data = conn.execute("""
                SELECT c.id, c.name, c.join_code as code, u.full_name as teacher_name, u.email as teacher_email
                FROM classrooms c
                JOIN users u ON c.created_by = u.id
                WHERE c.join_code = ?
            """, (code,)).fetchone()
            
            if classroom_data:
                classroom = dict(classroom_data)
                student = {
                    'name': current_user.name,
                    'email': current_user.email
                }
                teacher = {
                    'name': classroom['teacher_name'],
                    'email': classroom['teacher_email']
                }
                
                # Send notifications
                email_service.notify_classroom_enrollment(classroom, student, teacher)
                
        except Exception as email_error:
            current_app.logger.error(f"Failed to send enrollment email notifications: {email_error}")
            # Don't fail the enrollment if email fails
    
    return jsonify({"ok": ok})

@class_bp.route("/<int:classroom_id>", methods=["GET"])
@login_required
def classroom_detail(classroom_id):
    """View detailed classroom page"""
    # Get classroom details
    classroom = get_classroom_detail(classroom_id, current_user.id)
    if not classroom:
        return "Classroom not found or access denied", 404
    
    # Get students and assignments
    students = get_classroom_students(classroom_id)
    assignments = get_classroom_assignments(classroom_id)
    
    return render_template("classroom_detail.html", 
                         classroom=classroom, 
                         students=students, 
                         assignments=assignments)

@class_bp.route("/delete/<int:classroom_id>", methods=["POST"])
@login_required
@role_required("teacher","admin")
def rooms_delete_by_id(classroom_id):
    """Delete classroom by ID (for classroom detail page)"""
    ok = delete_classroom(classroom_id, current_user.id)
    return jsonify({"ok": ok})
