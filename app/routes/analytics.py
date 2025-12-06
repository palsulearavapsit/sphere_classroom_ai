"""
Analytics Dashboard Routes
Advanced data visualization and educational insights
"""
from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from ..roles import role_required
from ..services.analytics_service import analytics_service

analytics_bp = Blueprint("analytics", __name__, template_folder="../templates")

@analytics_bp.route("/", methods=["GET"])
@login_required
def analytics_home():
    """Main analytics dashboard"""
    if current_user.role == 'student':
        # Student sees personal analytics
        return render_template("analytics_student.html")
    elif current_user.role == 'teacher':
        # Teacher sees classroom analytics
        return render_template("analytics_teacher.html")
    else:
        # Admin sees system analytics
        return render_template("analytics_admin.html")

@analytics_bp.route("/student/<int:student_id>", methods=["GET"])
@login_required
@role_required("teacher", "admin")
def student_analytics(student_id):
    """Individual student analytics"""
    report = analytics_service.generate_performance_report(student_id)
    return render_template("analytics_student_detail.html", report=report, student_id=student_id)

@analytics_bp.route("/api/performance-chart/<chart_type>", methods=["GET"])
@login_required
def get_performance_chart(chart_type):
    """Get chart data for visualization"""
    valid_types = ["student_performance", "assessment_analytics", "learning_progress"]
    
    if chart_type not in valid_types:
        return jsonify({"error": "Invalid chart type"}), 400
    
    chart_data = analytics_service.create_performance_chart(chart_type)
    return jsonify({"chart": chart_data})

@analytics_bp.route("/api/student-performance", methods=["GET"])
@login_required
def get_student_performance():
    """Get student performance data"""
    if current_user.role == 'student':
        # Students can only see their own data
        data = analytics_service.get_student_performance_overview(current_user.id)
    else:
        # Teachers and admins see all data
        data = analytics_service.get_student_performance_overview()
    
    return jsonify(data)

@analytics_bp.route("/api/assessment-analytics", methods=["GET"])
@login_required
@role_required("teacher", "admin")
def get_assessment_analytics():
    """Get assessment analytics data"""
    data = analytics_service.get_assessment_analytics()
    return jsonify(data)

@analytics_bp.route("/api/system-stats", methods=["GET"])
@login_required
@role_required("admin")
def get_system_stats():
    """Get system-wide statistics"""
    stats = analytics_service.get_system_analytics()
    return jsonify(stats)

@analytics_bp.route("/api/classroom/<int:classroom_id>", methods=["GET"])
@login_required
@role_required("teacher", "admin")
def get_classroom_analytics(classroom_id):
    """Get classroom-specific analytics"""
    data = analytics_service.get_classroom_analytics(classroom_id)
    return jsonify(data)

@analytics_bp.route("/export/student/<int:student_id>", methods=["GET"])
@login_required
@role_required("teacher", "admin")
def export_student_report(student_id):
    """Export student performance report"""
    report = analytics_service.generate_performance_report(student_id)
    
    # For now, return JSON. Could be extended to PDF/Excel export
    return jsonify(report)

@analytics_bp.route("/api/recommendations/<int:student_id>", methods=["GET"])
@login_required
def get_recommendations(student_id):
    """Get AI-powered recommendations for student"""
    # Verify access rights
    if current_user.role == 'student' and current_user.id != student_id:
        return jsonify({"error": "Access denied"}), 403
    
    report = analytics_service.generate_performance_report(student_id)
    
    if "error" in report:
        return jsonify(report), 404
    
    return jsonify({
        "recommendations": report.get("recommendations", []),
        "performance_summary": report.get("performance_summary", {})
    })