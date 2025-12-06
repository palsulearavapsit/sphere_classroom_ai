from flask import Blueprint, render_template, request, jsonify, flash
from flask_login import login_required, current_user
from ..roles import role_required
from ..services.image_analysis_service import image_analysis_service
import base64

image_analysis_bp = Blueprint("image_analysis", __name__, template_folder="../templates")

@image_analysis_bp.route("/", methods=["GET"])
@login_required
def image_analysis_dashboard():
    recent_analyses = image_analysis_service.get_analysis_history(limit=10)
    
    return render_template("image_analysis_dashboard.html", 
                         recent_analyses=recent_analyses)

@image_analysis_bp.route("/analyze", methods=["POST"])
@login_required
def analyze_image():
    try:
        image_file = None
        possible_names = ['image', 'imageFile', 'file']
        
        for name in possible_names:
            if name in request.files:
                image_file = request.files[name]
                break
        
        if not image_file:
            return jsonify({
                "success": False, 
                "error": "No image file provided"
            }), 400
        
        if image_file.filename == '':
            return jsonify({"success": False, "error": "No file selected"}), 400
        
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/bmp', 'image/webp']
        file_type = image_file.content_type
        
        if file_type not in allowed_types:
            return jsonify({"success": False, "error": f"Unsupported file type: {file_type}"}), 400
        
        analysis_type = request.form.get('analysis_type', 'general')
        context = request.form.get('context', '') or request.form.get('custom_prompt', '')
        
        image_data = image_file.read()
        
        if len(image_data) == 0:
            return jsonify({"success": False, "error": "Empty file"}), 400
        
        result = image_analysis_service.analyze_image(
            image_data=image_data,
            analysis_type=analysis_type,
            context=context
        )
        
        return jsonify(result)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"EXCEPTION in analyze_image: {str(e)}")
        print(f"Full traceback: {error_details}")
        current_app.logger.error(f"Image analysis error: {str(e)}")
        current_app.logger.error(f"Traceback: {error_details}")
        return jsonify({
            "success": False, 
            "error": str(e),
            "debug": "Check server logs for detailed error information"
        }), 500

@image_analysis_bp.route("/analyze-base64", methods=["POST"])
@login_required
def analyze_base64_image():
    """Analyze base64 encoded image"""
    try:
        data = request.get_json() or {}
        
        image_base64 = data.get('image_data', '')
        analysis_type = data.get('analysis_type', 'general')
        context = data.get('context', '')
        
        if not image_base64:
            return jsonify({"success": False, "error": "No image data provided"}), 400
        
        # Remove data URL prefix if present
        if ',' in image_base64:
            image_base64 = image_base64.split(',')[1]
        
        # Decode base64 data
        try:
            image_data = base64.b64decode(image_base64)
        except Exception as e:
            return jsonify({"success": False, "error": "Invalid base64 image data"}), 400
        
        # Perform AI analysis
        result = image_analysis_service.analyze_image(
            image_data=image_data,
            analysis_type=analysis_type,
            context=context
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@image_analysis_bp.route("/math", methods=["POST"])
@login_required
def analyze_math():
    """Specialized mathematical equation analysis"""
    try:
        if 'image' not in request.files:
            return jsonify({"success": False, "error": "No image file provided"}), 400
        
        file = request.files['image']
        image_data = file.read()
        
        result = image_analysis_service.analyze_mathematical_equation(image_data)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@image_analysis_bp.route("/science", methods=["POST"])
@login_required
def analyze_science():
    """Specialized scientific diagram analysis"""
    try:
        if 'image' not in request.files:
            return jsonify({"success": False, "error": "No image file provided"}), 400
        
        file = request.files['image']
        image_data = file.read()
        
        result = image_analysis_service.analyze_scientific_diagram(image_data)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@image_analysis_bp.route("/text", methods=["POST"])
@login_required
def extract_text():
    """OCR text extraction from image"""
    try:
        if 'image' not in request.files:
            return jsonify({"success": False, "error": "No image file provided"}), 400
        
        file = request.files['image']
        image_data = file.read()
        
        result = image_analysis_service.extract_text_from_image(image_data)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@image_analysis_bp.route("/chart", methods=["POST"])
@login_required
def analyze_chart():
    """Chart and graph analysis"""
    try:
        if 'image' not in request.files:
            return jsonify({"success": False, "error": "No image file provided"}), 400
        
        file = request.files['image']
        image_data = file.read()
        
        result = image_analysis_service.analyze_chart_or_graph(image_data)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@image_analysis_bp.route("/history", methods=["GET"])
@login_required
def analysis_history():
    """Get analysis history"""
    try:
        limit = request.args.get('limit', 20, type=int)
        history = image_analysis_service.get_analysis_history(limit)
        
        return jsonify({
            "success": True,
            "history": history
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@image_analysis_bp.route("/result/<int:analysis_id>", methods=["GET"])
@login_required
def get_analysis_result(analysis_id):
    """Get specific analysis result"""
    try:
        result = image_analysis_service.get_analysis_by_id(analysis_id)
        
        if result:
            return jsonify({
                "success": True,
                "analysis": result
            })
        else:
            return jsonify({"success": False, "error": "Analysis not found"}), 404
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@image_analysis_bp.route("/bulk-analyze", methods=["POST"])
@login_required
@role_required('teacher', 'admin')
def bulk_analyze():
    """Bulk image analysis for multiple files"""
    try:
        if 'images' not in request.files:
            return jsonify({"success": False, "error": "No image files provided"}), 400
        
        files = request.files.getlist('images')
        analysis_type = request.form.get('analysis_type', 'general')
        context = request.form.get('context', '')
        
        if len(files) == 0:
            return jsonify({"success": False, "error": "No files selected"}), 400
        
        results = []
        processed = 0
        
        for file in files:
            try:
                if file.filename == '':
                    continue
                
                image_data = file.read()
                if len(image_data) == 0:
                    continue
                
                result = image_analysis_service.analyze_image(
                    image_data=image_data,
                    analysis_type=analysis_type,
                    context=context
                )
                
                results.append({
                    "filename": file.filename,
                    "analysis": result,
                    "status": "completed"
                })
                
                processed += 1
                
            except Exception as e:
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "error": str(e)
                })
        
        return jsonify({
            "success": True,
            "processed": processed,
            "total": len(files),
            "results": results
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@image_analysis_bp.route("/capabilities", methods=["GET"])
@login_required
def get_capabilities():
    """Get AI image analysis capabilities"""
    capabilities = {
        "analysis_types": {
            "math": {
                "name": "Mathematical Analysis",
                "description": "Analyze equations, formulas, graphs, and mathematical notation",
                "features": ["Equation solving", "Step-by-step solutions", "Concept identification"]
            },
            "science": {
                "name": "Scientific Analysis", 
                "description": "Analyze scientific diagrams, lab equipment, and processes",
                "features": ["Concept identification", "Process explanation", "Equipment recognition"]
            },
            "diagram": {
                "name": "Diagram Analysis",
                "description": "Analyze flowcharts, organizational charts, and technical diagrams",
                "features": ["Structure analysis", "Flow identification", "Component mapping"]
            },
            "chart": {
                "name": "Chart & Graph Analysis",
                "description": "Analyze data visualizations, trends, and statistics",
                "features": ["Data extraction", "Trend analysis", "Statistical insights"]
            },
            "text": {
                "name": "Text Extraction (OCR)",
                "description": "Extract and analyze text from images",
                "features": ["Text recognition", "Document analysis", "Content extraction"]
            },
            "general": {
                "name": "General Analysis",
                "description": "Comprehensive analysis for any type of educational content",
                "features": ["Content description", "Educational relevance", "Multi-domain analysis"]
            }
        },
        "supported_formats": ["JPEG", "PNG", "GIF", "WebP"],
        "max_file_size": "10MB",
        "ai_model": "Google Gemini 1.5 Flash Vision"
    }
    
    return jsonify({
        "success": True,
        "capabilities": capabilities
    })

@image_analysis_bp.route("/batch", methods=["POST"])
@login_required
def batch_analyze_images():
    """Alias for bulk-analyze to match frontend calls"""
    return bulk_analyze_images()