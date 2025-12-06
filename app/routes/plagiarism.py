"""
Plagiarism Detection Routes
Provides endpoints for AI-powered plagiarism checking and management
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from ..roles import role_required
from ..services.plagiarism_service import plagiarism_service
from ..db import get_db

plagiarism_bp = Blueprint("plagiarism", __name__, template_folder="../templates")

@plagiarism_bp.route("/", methods=["GET"])
@login_required
@role_required('teacher', 'admin')
def plagiarism_dashboard():
    """Main plagiarism detection dashboard"""
    try:
        # Get recent plagiarism checks with string-based timestamp handling
        db = get_db()
        recent_checks = db.execute("""
            SELECT pc.id, pc.user_id, pc.assignment_id, pc.text_hash, 
                   pc.content_sample, pc.plagiarism_score, pc.analysis_data,
                   pc.created_at as created_at_str, u.email as user_email, a.title as assignment_title
            FROM plagiarism_checks pc
            LEFT JOIN users u ON pc.user_id = u.id
            LEFT JOIN assignments a ON pc.assignment_id = a.id
            ORDER BY pc.id DESC
            LIMIT 20
        """).fetchall()
        
        # Get plagiarism statistics
        stats = db.execute("""
            SELECT 
                COUNT(*) as total_checks,
                COALESCE(AVG(plagiarism_score), 0) as avg_score,
                SUM(CASE WHEN plagiarism_score >= 0.8 THEN 1 ELSE 0 END) as high_risk,
                SUM(CASE WHEN plagiarism_score >= 0.6 AND plagiarism_score < 0.8 THEN 1 ELSE 0 END) as medium_risk,
                SUM(CASE WHEN plagiarism_score < 0.6 THEN 1 ELSE 0 END) as low_risk
            FROM plagiarism_checks
        """).fetchone()
        
    except Exception as e:
        # Handle database errors gracefully
        current_app.logger.error(f"Database error in plagiarism dashboard: {e}")
        recent_checks = []
        stats = {
            'total_checks': 0,
            'avg_score': 0,
            'high_risk': 0,
            'medium_risk': 0,
            'low_risk': 0
        }
    
    return render_template("plagiarism_dashboard.html", 
                         recent_checks=recent_checks,
                         stats=dict(stats) if stats else {})

@plagiarism_bp.route("/check", methods=["POST"])
@login_required
def check_plagiarism():
    """Check text for plagiarism"""
    data = request.get_json() or {}
    text = data.get("text", "").strip()
    assignment_id = data.get("assignment_id")
    exclude_user = data.get("exclude_user_id")
    
    if not text:
        return jsonify({"error": "No text provided"}), 400
    
    if len(text) < 50:
        return jsonify({"error": "Text too short for meaningful analysis"}), 400
    
    try:
        # Perform plagiarism check
        result = plagiarism_service.check_plagiarism(
            text=text,
            user_id=current_user.id,
            assignment_id=assignment_id,
            exclude_user_id=exclude_user
        )
        
        return jsonify({
            "success": True,
            "result": result
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@plagiarism_bp.route("/check-submission/<int:submission_id>", methods=["POST"])
@login_required
@role_required('teacher', 'admin')
def check_submission_plagiarism(submission_id):
    """Check a specific assignment submission for plagiarism"""
    db = get_db()
    
    # Get submission details
    submission = db.execute("""
        SELECT s.*, a.title as assignment_title, u.email as user_email
        FROM assessment_submissions s
        JOIN assessments a ON s.assessment_id = a.id
        JOIN users u ON s.user_id = u.id
        WHERE s.id = ?
    """, (submission_id,)).fetchone()
    
    if not submission:
        return jsonify({"error": "Submission not found"}), 404
    
    try:
        # Check plagiarism excluding the same user (for resubmissions)
        result = plagiarism_service.check_plagiarism(
            text=submission['content'],
            user_id=submission['user_id'],
            assignment_id=submission['assessment_id'],
            exclude_user_id=submission['user_id']
        )
        
        # Update submission with plagiarism score
        db.execute("""
            UPDATE assessment_submissions 
            SET plagiarism_score = ?, plagiarism_checked = 1
            WHERE id = ?
        """, (result['overall_score'], submission_id))
        db.commit()
        
        return jsonify({
            "success": True,
            "submission": dict(submission),
            "result": result
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@plagiarism_bp.route("/batch-check", methods=["POST"])
@login_required
@role_required('teacher', 'admin')
def batch_check_plagiarism():
    """Check multiple submissions for plagiarism"""
    data = request.get_json() or {}
    assignment_id = data.get("assignment_id")
    
    if not assignment_id:
        return jsonify({"error": "Assignment ID required"}), 400
    
    db = get_db()
    
    # Get all submissions for the assignment
    submissions = db.execute("""
        SELECT s.*, u.email as user_email
        FROM assessment_submissions s
        JOIN users u ON s.user_id = u.id
        WHERE s.assessment_id = ? AND LENGTH(s.content) > 50
        ORDER BY s.created_at DESC
    """, (assignment_id,)).fetchall()
    
    if not submissions:
        return jsonify({"error": "No submissions found for this assignment"}), 404
    
    results = []
    processed = 0
    
    try:
        for submission in submissions:
            try:
                # Check each submission
                result = plagiarism_service.check_plagiarism(
                    text=submission['content'],
                    user_id=submission['user_id'],
                    assignment_id=assignment_id,
                    exclude_user_id=submission['user_id']
                )
                
                # Update submission with plagiarism score
                db.execute("""
                    UPDATE assessment_submissions 
                    SET plagiarism_score = ?, plagiarism_checked = 1
                    WHERE id = ?
                """, (result['overall_score'], submission['id']))
                
                results.append({
                    "submission_id": submission['id'],
                    "user_email": submission['user_email'],
                    "plagiarism_score": result['overall_score'],
                    "risk_level": result['risk_level'],
                    "matches_found": len(result.get('database_matches', [])),
                    "status": "completed"
                })
                
                processed += 1
                
            except Exception as e:
                results.append({
                    "submission_id": submission['id'],
                    "user_email": submission['user_email'],
                    "status": "error",
                    "error": str(e)
                })
        
        db.commit()
        
        return jsonify({
            "success": True,
            "processed": processed,
            "total": len(submissions),
            "results": results
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@plagiarism_bp.route("/history", methods=["GET"])
@login_required
def plagiarism_history():
    """Get plagiarism check history for current user"""
    try:
        history = plagiarism_service.get_plagiarism_history(current_user.id)
        return jsonify({
            "success": True,
            "history": history
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@plagiarism_bp.route("/report/<int:check_id>", methods=["GET"])
@login_required
def plagiarism_report(check_id):
    """Get detailed plagiarism report"""
    db = get_db()
    
    # Get check details
    check = db.execute("""
        SELECT pc.*, u.email as user_email, a.title as assignment_title
        FROM plagiarism_checks pc
        LEFT JOIN users u ON pc.user_id = u.id
        LEFT JOIN assessments a ON pc.assignment_id = a.id
        WHERE pc.id = ?
    """, (check_id,)).fetchone()
    
    if not check:
        return jsonify({"error": "Plagiarism check not found"}), 404
    
    # Check permissions
    if current_user.role not in ['teacher', 'admin'] and check['user_id'] != current_user.id:
        return jsonify({"error": "Access denied"}), 403
    
    return jsonify({
        "success": True,
        "check": dict(check)
    })

@plagiarism_bp.route("/similarity/<int:submission_id>", methods=["GET"])
@login_required
@role_required('teacher', 'admin')
def submission_similarity(submission_id):
    """Get similarity analysis between submissions"""
    db = get_db()
    
    # Get the target submission
    target = db.execute("""
        SELECT s.*, u.email as user_email, a.title as assignment_title
        FROM assessment_submissions s
        JOIN users u ON s.user_id = u.id
        JOIN assessments a ON s.assessment_id = a.id
        WHERE s.id = ?
    """, (submission_id,)).fetchone()
    
    if not target:
        return jsonify({"error": "Submission not found"}), 404
    
    # Get other submissions for comparison
    other_submissions = db.execute("""
        SELECT s.*, u.email as user_email
        FROM assessment_submissions s
        JOIN users u ON s.user_id = u.id
        WHERE s.assessment_id = ? AND s.id != ? AND LENGTH(s.content) > 50
    """, (target['assessment_id'], submission_id)).fetchall()
    
    similarities = []
    
    try:
        for other in other_submissions:
            similarity_score = plagiarism_service._calculate_text_similarity(
                target['content'], 
                other['content']
            )
            
            if similarity_score > 0.2:  # Only show significant similarities
                similarities.append({
                    "submission_id": other['id'],
                    "user_email": other['user_email'],
                    "similarity_score": similarity_score,
                    "created_at": other['created_at']
                })
        
        # Sort by similarity score
        similarities.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        return jsonify({
            "success": True,
            "target_submission": dict(target),
            "similarities": similarities[:10]  # Top 10 most similar
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@plagiarism_bp.route("/settings", methods=["GET", "POST"])
@login_required
@role_required('admin')
def plagiarism_settings():
    """Manage plagiarism detection settings"""
    if request.method == "GET":
        # Get current settings (could be stored in database or config)
        settings = {
            "similarity_threshold": 0.7,
            "min_chunk_size": 50,
            "auto_check_submissions": True,
            "notification_threshold": 0.8
        }
        return jsonify({"success": True, "settings": settings})
    
    elif request.method == "POST":
        data = request.get_json() or {}
        
        # Update settings (implement storage mechanism as needed)
        # For now, return success
        return jsonify({
            "success": True,
            "message": "Settings updated successfully"
        })