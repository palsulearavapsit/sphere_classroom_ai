from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import io
from ..services.content_generation_service import content_generation_service
from ..roles import role_required

content_bp = Blueprint("content", __name__, template_folder="../templates")

@content_bp.route("/", methods=["GET"])
@login_required
def content_generation_home():
    role = current_user.role
    
    if role == "student":
        return render_template("content_generation_student.html")
    elif role in ["teacher", "admin"]:
        return render_template("content_generation_dashboard.html")
    else:
        from flask import abort
        abort(403)

@content_bp.route("/generate-quiz", methods=["POST"])
@login_required
@role_required("teacher", "admin")
def generate_quiz_questions():
    try:
        # Handle file upload or text input
        if 'pdf_file' in request.files and request.files['pdf_file'].filename:
            # PDF upload
            pdf_file = request.files['pdf_file']
            num_questions = int(request.form.get('num_questions', 5))
            question_type = request.form.get('question_type', 'mixed')
            
            if not pdf_file.filename.lower().endswith('.pdf'):
                return jsonify({"error": "Only PDF files are allowed"}), 400
            
            # Generate from PDF
            result = content_generation_service.generate_from_pdf(
                pdf_file,
                content_type="quiz_questions",
                num_questions=num_questions,
                question_type=question_type
            )
            
        else:
            # Text input
            data = request.get_json() or {}
            content = data.get('content', '').strip()
            num_questions = data.get('num_questions', 5)
            question_type = data.get('question_type', 'mixed')
            
            if not content:
                return jsonify({"error": "No content provided"}), 400
            
            result = content_generation_service.generate_quiz_questions(
                content, num_questions, question_type
            )
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Quiz generation error: {e}")
        return jsonify({"error": f"Failed to generate quiz: {str(e)}"}), 500

@content_bp.route("/generate-study-guide", methods=["POST"])
@login_required
def generate_study_guide():
    """Generate study guide from content"""
    try:
        if 'pdf_file' in request.files and request.files['pdf_file'].filename:
            # PDF upload
            pdf_file = request.files['pdf_file']
            title = request.form.get('title', 'Study Guide')
            
            if not pdf_file.filename.lower().endswith('.pdf'):
                return jsonify({"error": "Only PDF files are allowed"}), 400
            
            result = content_generation_service.generate_from_pdf(
                pdf_file,
                content_type="study_guide",
                title=title
            )
            
        else:
            # Text input
            data = request.get_json() or {}
            content = data.get('content', '').strip()
            title = data.get('title', 'Study Guide')
            
            if not content:
                return jsonify({"error": "No content provided"}), 400
            
            result = content_generation_service.generate_study_guide(content, title)
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Study guide generation error: {e}")
        return jsonify({"error": f"Failed to generate study guide: {str(e)}"}), 500

@content_bp.route("/generate-flashcards", methods=["POST"])
@login_required
def generate_flashcards():
    """Generate flashcards from content"""
    try:
        if 'pdf_file' in request.files and request.files['pdf_file'].filename:
            # PDF upload
            pdf_file = request.files['pdf_file']
            num_cards = int(request.form.get('num_cards', 10))
            
            if not pdf_file.filename.lower().endswith('.pdf'):
                return jsonify({"error": "Only PDF files are allowed"}), 400
            
            result = content_generation_service.generate_from_pdf(
                pdf_file,
                content_type="flashcards",
                num_cards=num_cards
            )
            
        else:
            # Text input
            data = request.get_json() or {}
            content = data.get('content', '').strip()
            num_cards = data.get('num_cards', 10)
            
            if not content:
                return jsonify({"error": "No content provided"}), 400
            
            result = content_generation_service.generate_flashcards(content, num_cards)
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Flashcards generation error: {e}")
        return jsonify({"error": f"Failed to generate flashcards: {str(e)}"}), 500

@content_bp.route("/generate-summary", methods=["POST"])
@login_required
def generate_summary():
    """Generate summary from content"""
    try:
        if 'pdf_file' in request.files and request.files['pdf_file'].filename:
            # PDF upload
            pdf_file = request.files['pdf_file']
            
            if not pdf_file.filename.lower().endswith('.pdf'):
                return jsonify({"error": "Only PDF files are allowed"}), 400
            
            result = content_generation_service.generate_from_pdf(
                pdf_file,
                content_type="summary"
            )
            
        else:
            # Text input
            data = request.get_json() or {}
            content = data.get('content', '').strip()
            
            if not content:
                return jsonify({"error": "No content provided"}), 400
            
            result = content_generation_service.generate_summary(content)
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Summary generation error: {e}")
        return jsonify({"error": f"Failed to generate summary: {str(e)}"}), 500

@content_bp.route("/generate-lesson-plan", methods=["POST"])
@login_required
@role_required("teacher", "admin")
def generate_lesson_plan():
    """Generate lesson plan from content"""
    try:
        if 'pdf_file' in request.files and request.files['pdf_file'].filename:
            # PDF upload
            pdf_file = request.files['pdf_file']
            duration = int(request.form.get('duration', 30))
            audience = request.form.get('audience', 'high school students')
            
            if not pdf_file.filename.lower().endswith('.pdf'):
                return jsonify({"error": "Only PDF files are allowed"}), 400
            
            result = content_generation_service.generate_from_pdf(
                pdf_file,
                content_type="lesson_plan",
                duration=duration,
                audience=audience
            )
            
        else:
            # Text input
            data = request.get_json() or {}
            content = data.get('content', '').strip()
            duration = data.get('duration', 30)
            audience = data.get('audience', 'high school students')
            
            if not content:
                return jsonify({"error": "No content provided"}), 400
            
            result = content_generation_service.generate_lesson_plan(content, duration, audience)
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Lesson plan generation error: {e}")
        return jsonify({"error": f"Failed to generate lesson plan: {str(e)}"}), 500

@content_bp.route("/generate-practice-problems", methods=["POST"])
@login_required
@role_required("teacher", "admin")
def generate_practice_problems():
    """Generate practice problems for a subject"""
    try:
        data = request.get_json() or {}
        subject = data.get('subject', '').strip()
        topic = data.get('topic', '').strip()
        difficulty = data.get('difficulty', 'medium')
        num_problems = data.get('num_problems', 5)
        
        if not subject or not topic:
            return jsonify({"error": "Subject and topic are required"}), 400
        
        result = content_generation_service.generate_practice_problems(
            subject, topic, difficulty, num_problems
        )
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Practice problems generation error: {e}")
        return jsonify({"error": f"Failed to generate practice problems: {str(e)}"}), 500

@content_bp.route("/enhance-content", methods=["POST"])
@login_required
@role_required("teacher", "admin")
def enhance_content():
    """Enhance content with examples"""
    try:
        data = request.get_json() or {}
        content = data.get('content', '').strip()
        num_examples = data.get('num_examples', 3)
        
        if not content:
            return jsonify({"error": "No content provided"}), 400
        
        result = content_generation_service.enhance_content_with_examples(content, num_examples)
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Content enhancement error: {e}")
        return jsonify({"error": f"Failed to enhance content: {str(e)}"}), 500

@content_bp.route("/bulk-generate", methods=["POST"])
@login_required
@role_required("teacher", "admin")
def bulk_content_generation():
    """Generate multiple types of content from a single source"""
    try:
        data = request.get_json() or {}
        content = data.get('content', '').strip()
        content_types = data.get('content_types', ['quiz_questions', 'study_guide'])
        
        if not content:
            return jsonify({"error": "No content provided"}), 400
        
        results = {}
        
        for content_type in content_types:
            if content_type == 'quiz_questions':
                results['quiz_questions'] = content_generation_service.generate_quiz_questions(content)
            elif content_type == 'study_guide':
                results['study_guide'] = content_generation_service.generate_study_guide(content)
            elif content_type == 'flashcards':
                results['flashcards'] = content_generation_service.generate_flashcards(content)
            elif content_type == 'summary':
                results['summary'] = content_generation_service.generate_summary(content)
        
        return jsonify({
            "success": True,
            "results": results,
            "generated_count": len(results)
        })
        
    except Exception as e:
        current_app.logger.error(f"Bulk generation error: {e}")
        return jsonify({"error": f"Failed to generate content: {str(e)}"}), 500

@content_bp.route("/save-generated-content", methods=["POST"])
@login_required
def save_generated_content():
    """Save generated content to database"""
    try:
        data = request.get_json() or {}
        content_data = data.get('content_data', {})
        content_type = data.get('content_type', '')
        title = data.get('title', f'Generated {content_type}')
        
        if not content_data:
            return jsonify({"error": "No content data provided"}), 400
        
        from ..db import get_db
        conn = get_db()
        
        # Save to a general content table (you might want to create this)
        conn.execute("""
            INSERT INTO generated_content (user_id, title, content_type, content_data, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, (current_user.id, title, content_type, json.dumps(content_data)))
        
        conn.commit()
        
        return jsonify({"success": True, "message": "Content saved successfully"})
        
    except Exception as e:
        current_app.logger.error(f"Content saving error: {e}")
        return jsonify({"error": f"Failed to save content: {str(e)}"}), 500

@content_bp.route("/my-generated-content", methods=["GET"])
@login_required
def my_generated_content():
    """Get user's generated content"""
    try:
        from ..db import get_db
        conn = get_db()
        
        content_items = conn.execute("""
            SELECT id, title, content_type, created_at
            FROM generated_content
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 50
        """, (current_user.id,)).fetchall()
        
        items = [dict(item) for item in content_items]
        
        return jsonify({"content_items": items})
        
    except Exception as e:
        current_app.logger.error(f"Content retrieval error: {e}")
        return jsonify({"error": f"Failed to retrieve content: {str(e)}"}), 500

@content_bp.route("/generate", methods=["POST"])
@login_required
@role_required("teacher", "admin")
def generate_content():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        content_type = request.form.get('content_type', 'quiz')
        difficulty = request.form.get('difficulty', 'intermediate')
        num_questions = int(request.form.get('num_questions', 10))
        
        # Generate content based on type
        if content_type == 'quiz':
            result = content_generation_service.generate_from_pdf(
                file,
                content_type="quiz_questions",
                num_questions=num_questions,
                difficulty=difficulty
            )
        elif content_type == 'study_guide':
            result = content_generation_service.generate_from_pdf(
                file,
                content_type="study_guide",
                difficulty=difficulty
            )
        elif content_type == 'summary':
            result = content_generation_service.generate_from_pdf(
                file,
                content_type="summary",
                difficulty=difficulty
            )
        elif content_type == 'flashcards':
            result = content_generation_service.generate_from_pdf(
                file,
                content_type="flashcards",
                num_questions=num_questions,
                difficulty=difficulty
            )
        else:
            return jsonify({"error": "Invalid content type"}), 400
        
        if result.get("success"):
            # Format the content properly based on type
            import json
            content_to_return = ""
            
            if content_type == 'quiz' and 'questions' in result:
                # Format quiz questions nicely
                questions = result['questions']
                content_to_return = f"Quiz Questions ({len(questions)} questions):\n\n"
                
                for i, q in enumerate(questions, 1):
                    content_to_return += f"Question {i}: {q.get('question', 'No question text')}\n"
                    
                    if q.get('type') == 'multiple_choice' and 'options' in q:
                        for key, value in q['options'].items():
                            content_to_return += f"  {key}) {value}\n"
                        content_to_return += f"  Correct Answer: {q.get('correct_answer', 'Not specified')}\n"
                        if q.get('explanation'):
                            content_to_return += f"  Explanation: {q['explanation']}\n"
                    elif q.get('answer'):
                        content_to_return += f"  Answer: {q['answer']}\n"
                    
                    content_to_return += f"  Difficulty: {q.get('difficulty', 'Not specified')}\n\n"
            else:
                # For other content types, use the content field or format the entire result
                content_to_return = result.get("content", json.dumps(result, indent=2))
            
            return jsonify({
                "success": True,
                "content": content_to_return,
                "raw_data": result  # Include raw data for debugging
            })
        else:
            return jsonify({
                "success": False,
                "error": result.get("error", "Failed to generate content")
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Content generation error: {e}")
        current_app.logger.error(f"Error type: {type(e).__name__}")
        import traceback
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "error": f"Failed to generate content: {str(e)}",
            "error_type": type(e).__name__
        }), 500

@content_bp.route("/generate-text", methods=["POST"])
@login_required
def generate_content_from_text():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        text = data.get('text', '').strip()
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        content_type = data.get('content_type', 'quiz')
        difficulty = data.get('difficulty', 'intermediate')
        num_questions = int(data.get('num_questions', 10))
        
        # Generate content based on type
        if content_type == 'quiz':
            result = content_generation_service.generate_from_text(
                text,
                content_type="quiz_questions",
                num_questions=num_questions,
                difficulty=difficulty
            )
        elif content_type == 'study_guide':
            result = content_generation_service.generate_from_text(
                text,
                content_type="study_guide",
                difficulty=difficulty
            )
        elif content_type == 'summary':
            result = content_generation_service.generate_from_text(
                text,
                content_type="summary",
                difficulty=difficulty
            )
        elif content_type == 'flashcards':
            result = content_generation_service.generate_from_text(
                text,
                content_type="flashcards",
                num_questions=num_questions,
                difficulty=difficulty
            )
        else:
            return jsonify({"error": "Invalid content type"}), 400
        
        if result.get("success"):
            return jsonify({
                "success": True,
                "content": result.get("content", "Content generated successfully!")
            })
        else:
            return jsonify({
                "success": False,
                "error": result.get("error", "Failed to generate content")
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Text content generation error: {e}")
        return jsonify({
            "success": False,
            "error": f"Failed to generate content: {str(e)}"
        }), 500