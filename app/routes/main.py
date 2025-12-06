from flask import Blueprint, render_template
from flask_login import login_required, current_user
from ..services.classrooms_service import list_enrolled, list_classrooms_for_teacher

main_bp = Blueprint("main", __name__, template_folder="../templates")

@main_bp.route("/")
@login_required
def home():
    role = current_user.role
    classrooms = []
    
    # Get classrooms for the user based on their role
    if role == "teacher":
        classrooms = list_classrooms_for_teacher(current_user.id)
        return render_template("dashboard_teacher.html", classrooms=classrooms)
    elif role == "admin":
        return render_template("dashboard_admin.html")
    else:  # student
        classrooms = list_enrolled(current_user.id)
        return render_template("dashboard_student.html", classrooms=classrooms)
