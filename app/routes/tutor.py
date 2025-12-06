from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from ..services.tutor_service import (
    chat_with_tutor, 
    list_sessions, 
    save_session,
    get_subject_context,
    get_difficulty_level,
    get_personalized_learning_suggestions,
    generate_step_by_step_explanation
)

tutor_bp = Blueprint("tutor", __name__, template_folder="../templates")

@tutor_bp.route("/", methods=["GET"])
@login_required
def tutor_home():
    sessions = list_sessions(current_user.id)
    return render_template("tutor.html", sessions=sessions)

@tutor_bp.route("/chat", methods=["POST"])
@login_required
def tutor_chat():
    data = request.get_json() or {}
    message = data.get("message","").strip()
    resp, session = chat_with_tutor(user_id=current_user.id, message=message)
    return jsonify({"reply": resp, "session": session})

@tutor_bp.route("/save", methods=["POST"])
@login_required
def tutor_save():
    data = request.get_json() or {}
    title = data.get("title","Session")
    sid = save_session(current_user.id, title)
    return jsonify({"session_id": sid})

@tutor_bp.route("/analyze", methods=["POST"])
@login_required
def analyze_question():
    """Analyze a question to provide subject context and difficulty level"""
    data = request.get_json() or {}
    message = data.get("message", "").strip()
    
    if not message:
        return jsonify({"error": "No message provided"}), 400
    
    subjects = get_subject_context(message)
    difficulty = get_difficulty_level(message, current_user.id)
    suggestions = get_personalized_learning_suggestions(current_user.id, subjects)
    
    return jsonify({
        "subjects": subjects,
        "difficulty": difficulty,
        "learning_suggestions": suggestions,
        "step_by_step_available": len(subjects) > 0
    })

@tutor_bp.route("/step-by-step", methods=["POST"])
@login_required
def get_step_by_step():
    """Get step-by-step explanation template for a subject"""
    data = request.get_json() or {}
    message = data.get("message", "").strip()
    
    if not message:
        return jsonify({"error": "No message provided"}), 400
    
    subjects = get_subject_context(message)
    if not subjects:
        return jsonify({"error": "No specific subject detected"}), 400
    
    explanation_template = generate_step_by_step_explanation(message, subjects)
    
    return jsonify({
        "template": explanation_template,
        "subjects": subjects,
        "message": "Step-by-step explanation template generated"
    })

@tutor_bp.route("/learning-path", methods=["GET"])
@login_required
def get_learning_path():
    """Get personalized learning suggestions for the user"""
    try:
        suggestions = get_personalized_learning_suggestions(current_user.id, [])
        
        return jsonify({
            "suggestions": suggestions,
            "user_id": current_user.id,
            "message": "Personalized learning path generated"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
