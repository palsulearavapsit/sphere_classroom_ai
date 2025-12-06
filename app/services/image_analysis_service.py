import os
import base64
import json
from datetime import datetime
from flask import current_app
from ..db import get_db
import google.generativeai as genai

class AIImageAnalysisService:
    def __init__(self):
        self.model = None
        self._initialize_vision_model()
        
    def init_ai(self):
        """Initialize AI for image analysis"""
        return self._initialize_vision_model()
        
    def _initialize_vision_model(self):
        """Initialize Google Gemini Vision model"""
        try:
            # Try multiple ways to get the API key
            api_key = None
            try:
                api_key = current_app.config.get('GEMINI_API_KEY') or current_app.config.get('GOOGLE_AI_API_KEY')
            except:
                # Fallback to environment variables if no Flask context
                api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_AI_API_KEY')
            
            if api_key:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-2.5-flash')
                return True
            else:
                return False
        except Exception as e:
            return False
    
    def analyze_image(self, image_data, analysis_type="general", context=""):
        if not self.model:
            return {
                "success": False,
                "error": "AI Vision model not available",
                "analysis": "Please configure Google AI API key"
            }
        
        try:
            # Convert image data to the format expected by Gemini
            if isinstance(image_data, str):
                # If it's a base64 string, decode it
                image_data = base64.b64decode(image_data)
            
            # Create image part for Gemini
            image_part = {
                "mime_type": "image/jpeg",  # Assume JPEG, could be enhanced to detect type
                "data": image_data
            }
            
            # Generate specialized prompt based on analysis type
            prompt = self._generate_analysis_prompt(analysis_type, context)
            
            # Call Gemini Vision API
            response = self.model.generate_content([prompt, image_part])
            
            # Parse and structure the response
            analysis_result = self._parse_vision_response(response.text, analysis_type)
            
            # Store analysis in database
            analysis_id = self._store_analysis(image_data, analysis_type, analysis_result)
            
            return {
                "success": True,
                "analysis_id": analysis_id,
                "analysis_type": analysis_type,
                "result": analysis_result,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            print(f"Image analysis error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "analysis": "Failed to analyze image"
            }
    
    def _generate_analysis_prompt(self, analysis_type, context):
        """Generate specialized prompts for different types of image analysis"""
        
        base_prompt = "You are an advanced AI educational assistant specializing in visual content analysis. "
        
        if analysis_type == "math":
            return f"""{base_prompt}

Analyze this mathematical image and provide a comprehensive response in JSON format:

{{
    "content_type": "mathematical",
    "equations_found": ["list of equations detected"],
    "mathematical_concepts": ["concepts involved"],
    "step_by_step_solution": "if solvable, provide step-by-step solution",
    "difficulty_level": "basic|intermediate|advanced",
    "educational_notes": "teaching points and explanations",
    "related_topics": ["related mathematical topics"],
    "confidence_score": 0.0-1.0
}}

Context: {context}

Focus on: equations, formulas, graphs, geometric figures, mathematical notation, problem-solving steps."""
        
        elif analysis_type == "science":
            return f"""{base_prompt}

Analyze this scientific image and provide a detailed response in JSON format:

{{
    "content_type": "scientific",
    "scientific_domain": "physics|chemistry|biology|earth_science",
    "key_concepts": ["main scientific concepts shown"],
    "observations": ["what can be observed in the image"],
    "scientific_principles": ["underlying principles"],
    "explanations": "detailed scientific explanation",
    "experimental_context": "if applicable, experimental setup or context",
    "educational_value": "learning objectives and teaching points",
    "confidence_score": 0.0-1.0
}}

Context: {context}

Focus on: scientific diagrams, lab equipment, experimental setups, natural phenomena, scientific processes."""
        
        elif analysis_type == "diagram":
            return f"""{base_prompt}

Analyze this diagram and provide structured information in JSON format:

{{
    "content_type": "diagram",
    "diagram_type": "flowchart|organizational|technical|conceptual|process",
    "main_components": ["key elements in the diagram"],
    "relationships": ["how components relate to each other"],
    "flow_or_process": "description of any process or flow shown",
    "text_elements": ["any text labels or annotations"],
    "educational_purpose": "likely teaching or learning objective",
    "clarity_assessment": "assessment of diagram clarity and effectiveness",
    "confidence_score": 0.0-1.0
}}

Context: {context}

Focus on: structure, flow, connections, labels, organizational elements."""
        
        elif analysis_type == "chart":
            return f"""{base_prompt}

Analyze this chart or graph and provide data insights in JSON format:

{{
    "content_type": "chart_graph",
    "chart_type": "bar|line|pie|scatter|histogram|other",
    "data_summary": "summary of data presented",
    "key_trends": ["main trends or patterns"],
    "data_points": ["specific values if readable"],
    "axes_labels": ["x and y axis labels if present"],
    "title_and_legends": "chart title and legend information",
    "insights": "analytical insights from the data",
    "educational_context": "likely use in educational setting",
    "confidence_score": 0.0-1.0
}}

Context: {context}

Focus on: data visualization, trends, statistics, quantitative information."""
        
        elif analysis_type == "text":
            return f"""{base_prompt}

Extract and analyze text from this image, providing structured results in JSON format:

{{
    "content_type": "text_document",
    "extracted_text": "full text extracted from image",
    "document_type": "handwritten|printed|mixed",
    "text_quality": "readability assessment",
    "key_information": ["main points or important information"],
    "educational_content": "if educational, what subject/topic",
    "language_detected": "primary language",
    "formatting_notes": "observations about formatting, structure",
    "confidence_score": 0.0-1.0
}}

Context: {context}

Focus on: accurate text extraction, document structure, educational content identification."""
        
        else:  # general analysis
            return f"""{base_prompt}

Provide a comprehensive general analysis of this image in JSON format:

{{
    "content_type": "general",
    "image_description": "detailed description of what's shown",
    "educational_relevance": "potential educational applications",
    "subject_areas": ["possible academic subjects this relates to"],
    "key_elements": ["main visual elements"],
    "text_present": "any text visible in the image",
    "recommended_analysis": "suggest more specific analysis type if applicable",
    "teaching_opportunities": "how this could be used in education",
    "confidence_score": 0.0-1.0
}}

Context: {context}

Provide a thorough analysis suitable for educational purposes."""
    
    def _parse_vision_response(self, response_text, analysis_type):
        """Parse and structure the AI vision response"""
        try:
            # Try to parse as JSON first
            if response_text.strip().startswith('{'):
                return json.loads(response_text)
            else:
                # If not JSON, structure the text response
                return {
                    "content_type": analysis_type,
                    "analysis": response_text,
                    "structured": False,
                    "confidence_score": 0.8
                }
        except json.JSONDecodeError:
            # Fallback to text analysis
            return {
                "content_type": analysis_type,
                "analysis": response_text,
                "structured": False,
                "confidence_score": 0.7,
                "note": "Response could not be parsed as structured data"
            }
    
    def _store_analysis(self, image_data, analysis_type, result):
        """Store image analysis in database for future reference"""
        db = get_db()
        
        try:
            # Create hash of image for deduplication
            import hashlib
            image_hash = hashlib.sha256(image_data).hexdigest()
            
            # Store analysis result
            db.execute("""
                INSERT INTO image_analyses 
                (image_hash, analysis_type, analysis_result, created_at)
                VALUES (?, ?, ?, ?)
            """, (
                image_hash,
                analysis_type,
                json.dumps(result),
                datetime.utcnow().isoformat()
            ))
            db.commit()
            
            analysis_id = db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
            return analysis_id
            
        except Exception as e:
            print(f"Error storing image analysis: {str(e)}")
            return None
    
    def get_analysis_history(self, limit=20):
        """Get recent image analysis history"""
        db = get_db()
        
        try:
            analyses = db.execute("""
                SELECT id, analysis_type, analysis_result, created_at
                FROM image_analyses 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,)).fetchall()
            
            results = []
            for analysis in analyses:
                try:
                    result_data = json.loads(analysis['analysis_result'])
                    results.append({
                        "id": analysis['id'],
                        "analysis_type": analysis['analysis_type'],
                        "result": result_data,
                        "created_at": analysis['created_at']
                    })
                except json.JSONDecodeError:
                    results.append({
                        "id": analysis['id'],
                        "analysis_type": analysis['analysis_type'],
                        "result": {"analysis": analysis['analysis_result']},
                        "created_at": analysis['created_at']
                    })
            
            return results
            
        except Exception as e:
            print(f"Error getting analysis history: {str(e)}")
            return []
    
    def analyze_mathematical_equation(self, image_data):
        """Specialized mathematical equation analysis"""
        return self.analyze_image(
            image_data, 
            analysis_type="math",
            context="Focus on solving equations and explaining mathematical concepts step by step"
        )
    
    def analyze_scientific_diagram(self, image_data):
        """Specialized scientific diagram analysis"""
        return self.analyze_image(
            image_data,
            analysis_type="science", 
            context="Identify scientific processes, experimental setups, and educational concepts"
        )
    
    def extract_text_from_image(self, image_data):
        """OCR text extraction with educational focus"""
        return self.analyze_image(
            image_data,
            analysis_type="text",
            context="Extract all text accurately for educational content analysis"
        )
    
    def analyze_chart_or_graph(self, image_data):
        """Data visualization analysis"""
        return self.analyze_image(
            image_data,
            analysis_type="chart",
            context="Analyze data trends, statistics, and educational insights from visual data"
        )
    
    def get_analysis_by_id(self, analysis_id):
        """Retrieve specific analysis by ID"""
        db = get_db()
        
        try:
            analysis = db.execute("""
                SELECT id, analysis_type, analysis_result, created_at
                FROM image_analyses 
                WHERE id = ?
            """, (analysis_id,)).fetchone()
            
            if analysis:
                return {
                    "id": analysis['id'],
                    "analysis_type": analysis['analysis_type'],
                    "result": json.loads(analysis['analysis_result']),
                    "created_at": analysis['created_at']
                }
            
            return None
            
        except Exception as e:
            print(f"Error getting analysis by ID: {str(e)}")
            return None

# Global service instance
image_analysis_service = AIImageAnalysisService()