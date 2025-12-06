"""
Auto-Grading Routes for Project Galileo
Handles AI-powered assignment grading and feedback
"""
import json
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from ..services.auto_grading_service import auto_grading_service
from ..services.assessments_service import fetch_test
from ..roles import role_required
from ..db import get_db

grading_bp = Blueprint("grading", __name__, template_folder="../templates")

@grading_bp.route("/", methods=["GET"])
@login_required
@role_required("teacher", "admin")
def grading_home():
    """Auto-grading dashboard for teachers"""
    conn = get_db()
    
    # Get assignments that need grading
    pending_assignments = conn.execute("""
        SELECT a.id, a.title, a.classroom_id, c.name as classroom_name,
               COUNT(s.id) as submission_count,
               COUNT(CASE WHEN s.ai_graded = 1 THEN 1 END) as ai_graded_count
        FROM assignments a
        LEFT JOIN classrooms c ON a.classroom_id = c.id
        LEFT JOIN submissions s ON a.id = s.assignment_id
        WHERE c.created_by = ? OR ? = 'admin'
        GROUP BY a.id, a.title, a.classroom_id, c.name
        ORDER BY a.created_at DESC
    """, (current_user.id, current_user.role)).fetchall()
    
    assignments = [dict(row) for row in pending_assignments]
    
    return render_template("auto_grading_dashboard.html", assignments=assignments)

@grading_bp.route("/grade/<int:assignment_id>", methods=["GET", "POST"])
@login_required
@role_required("teacher", "admin")
def grade_assignment(assignment_id):
    """Grade specific assignment submissions"""
    conn = get_db()
    
    if request.method == "GET":
        # Get assignment details and submissions
        assignment = conn.execute("""
            SELECT a.*, c.name as classroom_name
            FROM assignments a
            LEFT JOIN classrooms c ON a.classroom_id = c.id
            WHERE a.id = ?
        """, (assignment_id,)).fetchone()
        
        if not assignment:
            return "Assignment not found", 404
        
        # Get submissions for this assignment
        submissions = conn.execute("""
            SELECT s.*, u.full_name as student_name, u.email as student_email
            FROM submissions s
            JOIN users u ON s.user_id = u.id
            WHERE s.assignment_id = ?
            ORDER BY s.submitted_at DESC
        """, (assignment_id,)).fetchall()
        
        assignment_dict = dict(assignment)
        submissions_list = [dict(sub) for sub in submissions]
        
        return render_template("grade_assignment.html", 
                             assignment=assignment_dict, 
                             submissions=submissions_list)
    
    elif request.method == "POST":
        # Auto-grade all submissions for this assignment
        data = request.get_json() or {}
        assignment_type = data.get('assignment_type', 'general')
        
        try:
            # Get assignment details
            assignment = conn.execute("""
                SELECT * FROM assignments WHERE id = ?
            """, (assignment_id,)).fetchone()
            
            if not assignment:
                return jsonify({"error": "Assignment not found"}), 404
            
            # Get ungraded submissions
            submissions = conn.execute("""
                SELECT s.*, u.full_name as student_name
                FROM submissions s
                JOIN users u ON s.user_id = u.id
                WHERE s.assignment_id = ? AND (s.ai_graded != 1 OR s.ai_graded IS NULL)
            """, (assignment_id,)).fetchall()
            
            graded_count = 0
            results = []
            
            for submission in submissions:
                # Extract student response from answers_json
                answers = json.loads(submission['answers_json'] or '{}')
                
                # Handle different answer formats
                if isinstance(answers, dict):
                    student_response = answers.get('essay_response', 
                                                 answers.get('text_response',
                                                           answers.get('answer', str(answers))))
                elif isinstance(answers, list):
                    # If it's a list, join the elements or take the first one
                    student_response = ' '.join(str(item) for item in answers) if answers else ''
                else:
                    # If it's a string or other type, convert to string
                    student_response = str(answers)
                
                # Grade with AI
                grading_result = auto_grading_service.grade_assignment(
                    assignment_type=assignment_type,
                    question=assignment['title'],  # Using title as question
                    student_response=student_response,
                    max_points=100
                )
                
                if not grading_result.get('error'):
                    # Update submission with AI grading
                    new_score = grading_result.get('score', 0)
                    feedback = grading_result.get('feedback', 'No feedback available')
                    
                    conn.execute("""
                        UPDATE submissions 
                        SET score = ?, ai_graded = 1, ai_feedback = ?
                        WHERE id = ?
                    """, (new_score, json.dumps(grading_result), submission['id']))
                    
                    graded_count += 1
                    results.append({
                        "student_name": submission['student_name'],
                        "score": new_score,
                        "feedback": feedback
                    })
            
            conn.commit()
            
            return jsonify({
                "success": True,
                "graded_count": graded_count,
                "total_submissions": len(submissions),
                "results": results
            })
            
        except Exception as e:
            current_app.logger.error(f"Auto-grading error: {e}")
            return jsonify({"error": f"Grading failed: {str(e)}"}), 500

@grading_bp.route("/grade-single", methods=["POST"])
@login_required
@role_required("teacher", "admin")
def grade_single_submission():
    """Grade a single submission"""
    data = request.get_json()
    
    try:
        submission_id = data.get('submission_id')
        assignment_type = data.get('assignment_type', 'general')
        question = data.get('question', '')
        student_response = data.get('student_response', '')
        answer_key = data.get('answer_key', '')
        
        # Grade with AI
        result = auto_grading_service.grade_assignment(
            assignment_type=assignment_type,
            question=question,
            student_response=student_response,
            answer_key=answer_key
        )
        
        if submission_id and not result.get('error'):
            # Save to database
            conn = get_db()
            conn.execute("""
                UPDATE submissions 
                SET score = ?, ai_graded = 1, ai_feedback = ?
                WHERE id = ?
            """, (result.get('score', 0), json.dumps(result), submission_id))
            conn.commit()
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Single grading error: {e}")
        return jsonify({"error": f"Grading failed: {str(e)}"}), 500

@grading_bp.route("/student-insights/<int:student_id>", methods=["GET"])
@login_required
@role_required("teacher", "admin")
def student_grading_insights(student_id):
    """Get AI insights for a specific student's performance"""
    conn = get_db()
    
    # Get student's grading history
    grading_history = conn.execute("""
        SELECT s.score, s.ai_feedback, a.title, s.submitted_at
        FROM submissions s
        JOIN assignments a ON s.assignment_id = a.id
        WHERE s.user_id = ? AND s.ai_graded = 1
        ORDER BY s.submitted_at DESC
        LIMIT 10
    """, (student_id,)).fetchall()
    
    if not grading_history:
        return jsonify({"error": "No grading history found"}), 404
    
    # Convert to list of dicts
    history = []
    for row in grading_history:
        history.append({
            "score": row['score'],
            "assignment": row['title'],
            "date": row['submitted_at']
        })
    
    try:
        insights = auto_grading_service.provide_improvement_suggestions(history)
        return jsonify(insights)
    except Exception as e:
        current_app.logger.error(f"Insights generation error: {e}")
        return jsonify({"error": f"Failed to generate insights: {str(e)}"}), 500

@grading_bp.route("/bulk-grade", methods=["POST"])
@login_required
@role_required("teacher", "admin")
def bulk_grade_assignments():
    """Grade multiple assignments in bulk"""
    data = request.get_json()
    assignments_data = data.get('assignments', [])
    
    if not assignments_data:
        return jsonify({"error": "No assignments provided"}), 400
    
    try:
        results = auto_grading_service.batch_grade_assignments(assignments_data)
        
        # Save results to database
        conn = get_db()
        for result in results:
            if not result.get('error') and result.get('assignment_id'):
                conn.execute("""
                    UPDATE submissions 
                    SET score = ?, ai_graded = 1, ai_feedback = ?
                    WHERE assignment_id = ? AND user_id = ?
                """, (
                    result.get('score', 0),
                    json.dumps(result),
                    result['assignment_id'],
                    result.get('student_id')
                ))
        
        conn.commit()
        
        return jsonify({
            "success": True,
            "results": results,
            "total_graded": len([r for r in results if not r.get('error')])
        })
        
    except Exception as e:
        current_app.logger.error(f"Bulk grading error: {e}")
        return jsonify({"error": f"Bulk grading failed: {str(e)}"}), 500

@grading_bp.route("/feedback-summary/<int:assignment_id>", methods=["GET"])
@login_required
@role_required("teacher", "admin")
def assignment_feedback_summary(assignment_id):
    """Get AI-generated summary of all feedback for an assignment"""
    conn = get_db()
    
    # Get all AI feedback for this assignment
    submissions = conn.execute("""
        SELECT s.ai_feedback, s.score, u.full_name as student_name
        FROM submissions s
        JOIN users u ON s.user_id = u.id
        WHERE s.assignment_id = ? AND s.ai_graded = 1 AND s.ai_feedback IS NOT NULL
    """, (assignment_id,)).fetchall()
    
    if not submissions:
        return jsonify({"error": "No AI-graded submissions found"}), 404
    
    # Aggregate data for summary
    scores = [row['score'] for row in submissions]
    feedback_data = {
        "average_score": sum(scores) / len(scores),
        "min_score": min(scores),
        "max_score": max(scores),
        "total_submissions": len(submissions),
        "score_distribution": {
            "A (90-100)": len([s for s in scores if s >= 90]),
            "B (80-89)": len([s for s in scores if 80 <= s < 90]),
            "C (70-79)": len([s for s in scores if 70 <= s < 80]),
            "D (60-69)": len([s for s in scores if 60 <= s < 70]),
            "F (0-59)": len([s for s in scores if s < 60])
        }
    }
    
    return jsonify(feedback_data)

@grading_bp.route("/submission/<int:submission_id>", methods=["GET"])
@login_required
@role_required("teacher", "admin")
def view_submission(submission_id):
    """View individual submission details"""
    conn = get_db()
    
    try:
        # Get submission details
        submission = conn.execute("""
            SELECT s.*, u.full_name as student_name, u.email as student_email,
                   a.title as assignment_title
            FROM submissions s
            JOIN users u ON s.user_id = u.id
            JOIN assignments a ON s.assignment_id = a.id
            WHERE s.id = ?
        """, (submission_id,)).fetchone()
        
        if not submission:
            return jsonify({"success": False, "error": "Submission not found"}), 404
        
        # Parse answers
        answers = json.loads(submission['answers_json'] or '{}')
        
        # Handle different answer formats
        if isinstance(answers, dict):
            answer_text = answers.get('answer', 
                                    answers.get('essay_response',
                                              answers.get('text_response', str(answers))))
        elif isinstance(answers, list):
            # If it's a list, join the elements or take the first one
            answer_text = ' '.join(str(item) for item in answers) if answers else ''
        else:
            # If it's a string or other type, convert to string
            answer_text = str(answers)
        
        submission_data = {
            "id": submission['id'],
            "student_name": submission['student_name'],
            "student_email": submission['student_email'],
            "assignment_title": submission['assignment_title'],
            "answer": answer_text,
            "score": submission['score'],
            "ai_graded": bool(submission['ai_graded']),
            "ai_feedback": submission['ai_feedback'],
            "manual_feedback": submission['manual_feedback'],
            "submitted_at": submission['submitted_at'] or submission['created_at']
        }
        
        return jsonify({"success": True, "submission": submission_data})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@grading_bp.route("/grade-submission/<int:submission_id>", methods=["POST"])
@login_required
@role_required("teacher", "admin")
def grade_individual_submission(submission_id):
    """Grade an individual submission"""
    conn = get_db()
    
    try:
        data = request.get_json() or {}
        assignment_type = data.get('assignment_type', 'general')
        
        # Get submission and assignment details
        submission = conn.execute("""
            SELECT s.*, a.content_json, a.title
            FROM submissions s
            JOIN assignments a ON s.assignment_id = a.id
            WHERE s.id = ?
        """, (submission_id,)).fetchone()
        
        if not submission:
            return jsonify({"success": False, "error": "Submission not found"}), 404
        
        # Parse submission content
        answers = json.loads(submission['answers_json'] or '{}')
        
        # Handle different answer formats
        if isinstance(answers, dict):
            answer_text = answers.get('answer', 
                                    answers.get('essay_response',
                                              answers.get('text_response', str(answers))))
        elif isinstance(answers, list):
            # If it's a list, join the elements or take the first one
            answer_text = ' '.join(str(item) for item in answers) if answers else ''
        else:
            # If it's a string or other type, convert to string
            answer_text = str(answers)
        
        # Parse assignment content
        assignment_content = json.loads(submission['content_json'] or '{}')
        question = assignment_content.get('question', '')
        
        # Grade the submission
        from ..services.auto_grading_service import auto_grading_service
        
        grading_result = auto_grading_service.grade_assignment(
            assignment_type=assignment_type,
            question=question,
            student_response=answer_text,
            max_points=assignment_content.get('max_points', 100),
            criteria=assignment_content.get('rubric', '')
        )
        
        if not grading_result.get('error'):
            # Update submission with AI grading
            new_score = grading_result['score']
            
            conn.execute("""
                UPDATE submissions 
                SET score = ?, ai_graded = 1, ai_feedback = ?, graded_at = datetime('now')
                WHERE id = ?
            """, (new_score, json.dumps(grading_result), submission_id))
            conn.commit()
            
            return jsonify({
                "success": True,
                "score": new_score,
                "feedback": grading_result.get('feedback', ''),
                "grade": grading_result.get('grade', '')
            })
        else:
            return jsonify({"success": False, "error": grading_result.get('error', 'Grading failed')})
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@grading_bp.route("/export/<int:assignment_id>", methods=["GET"])
@login_required
@role_required("teacher", "admin")
def export_assignment_results(assignment_id):
    """Export assignment results as CSV"""
    from flask import Response
    import csv
    from io import StringIO
    
    conn = get_db()
    
    try:
        # Get assignment and submissions
        assignment = conn.execute("""
            SELECT title FROM assignments WHERE id = ?
        """, (assignment_id,)).fetchone()
        
        if not assignment:
            return "Assignment not found", 404
        
        submissions = conn.execute("""
            SELECT s.*, u.full_name as student_name, u.email as student_email
            FROM submissions s
            JOIN users u ON s.user_id = u.id
            WHERE s.assignment_id = ?
            ORDER BY u.full_name
        """, (assignment_id,)).fetchall()
        
        # Create CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Student Name', 'Email', 'Score', 'AI Graded', 'Submitted At', 'Graded At'])
        
        # Write data
        for submission in submissions:
            writer.writerow([
                submission['student_name'],
                submission['student_email'],
                submission['score'],
                'Yes' if submission['ai_graded'] else 'No',
                submission['submitted_at'] or submission['created_at'],
                submission['graded_at'] or ''
            ])
        
        # Create response
        output.seek(0)
        response = Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={assignment["title"]}_results.csv'}
        )
        
        return response
        
    except Exception as e:
        return f"Export failed: {str(e)}", 500