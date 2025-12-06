from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required
from ..roles import role_required
from ..services.admin_service import list_users, create_user, update_user, delete_user, db_status
from ..services.email_service import email_service

admin_bp = Blueprint("admin", __name__, template_folder="../templates")

@admin_bp.route("/", methods=["GET"])
@login_required
@role_required("admin")
def admin_home():
    users = list_users()
    return render_template("admin_users.html", users=users)

@admin_bp.route("/users", methods=["GET","POST","PUT","DELETE"])
@login_required
@role_required("admin")
def admin_users():
    if request.method == "GET":
        return jsonify({"users": list_users()})
    data = request.get_json() or {}
    if request.method == "POST":
        return jsonify(create_user(data))
    if request.method == "PUT":
        return jsonify(update_user(data))
    if request.method == "DELETE":
        return jsonify({"ok": delete_user(data.get("id"))})

@admin_bp.route("/status", methods=["GET"])
@login_required
@role_required("admin")
def admin_status():
    return jsonify(db_status())

@admin_bp.route("/users/create", methods=["POST"])
@login_required
@role_required("admin")
def admin_create_user():
    """Create a new user"""
    data = request.get_json() or {}
    result = create_user(data)
    
    # Send welcome email to new user
    if result.get('success') and current_app.config.get('SEND_EMAIL_NOTIFICATIONS', True):
        try:
            user_data = {
                'name': data.get('name'),
                'email': data.get('email'),
                'role': data.get('role')
            }
            password = data.get('password')  # Send password only if it was auto-generated
            
            email_service.notify_user_created(user_data, password)
            
        except Exception as email_error:
            current_app.logger.error(f"Failed to send welcome email: {email_error}")
            # Don't fail user creation if email fails
    
    return jsonify(result)

@admin_bp.route("/users/delete/<int:user_id>", methods=["POST"])
@login_required
@role_required("admin")
def admin_delete_user(user_id):
    """Delete a user by ID"""
    result = delete_user(user_id)
    return jsonify({"success": result, "message": "User deleted successfully" if result else "Failed to delete user"})
