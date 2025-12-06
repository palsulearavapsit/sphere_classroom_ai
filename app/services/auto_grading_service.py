try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    GENAI_AVAILABLE = False
    print("Warning: Google Generative AI not available")

from flask import current_app
import json
import re
from datetime import datetime

class AutoGradingService:
    def __init__(self):
        self.model = None
        self.grading_prompts = {
            'essay': """
You are an expert teacher grading a student essay. Please evaluate this essay and provide:

1. OVERALL SCORE (0-100)
2. DETAILED FEEDBACK including:
   - Strengths of the essay
   - Areas for improvement
   - Writing quality assessment
   - Content accuracy and depth
   - Grammar and style notes

3. RUBRIC BREAKDOWN:
   - Content Quality (25 points)
   - Organization (25 points)
   - Writing Mechanics (25 points)
   - Creativity/Originality (25 points)

Essay Question: {question}
Student Response: {response}

Please format your response as JSON:
{{
    "overall_score": 85,
    "grade_letter": "B+",
    "feedback": {{
        "strengths": ["Strong introduction", "Clear thesis statement"],
        "improvements": ["Add more supporting examples", "Improve conclusion"],
        "writing_quality": "Good vocabulary and sentence structure",
        "content_assessment": "Demonstrates understanding of key concepts"
    }},
    "rubric_scores": {{
        "content_quality": 22,
        "organization": 21,
        "writing_mechanics": 20,
        "creativity": 22
    }},
    "detailed_comments": "This essay shows a solid understanding of the topic..."
}}
""",
            'short_answer': """
You are grading a short answer response. Evaluate for accuracy, completeness, and clarity.

Question: {question}
Expected Answer/Key Points: {answer_key}
Student Response: {response}

Provide a score out of {max_points} points and brief feedback.

Format as JSON:
{{
    "score": 8,
    "max_points": 10,
    "percentage": 80,
    "feedback": "Correct main concept but missing key detail about...",
    "key_points_covered": ["Point 1", "Point 2"],
    "missing_points": ["Point 3"],
    "suggestions": "Consider adding more detail about..."
}}
""",
            'math_problem': """
You are grading a mathematics problem. Check the solution for:
1. Correct method/approach
2. Accurate calculations
3. Proper notation
4. Final answer correctness

Problem: {question}
Correct Solution: {answer_key}
Student Work: {response}

Format as JSON:
{{
    "score": 9,
    "max_points": 10,
    "method_correct": true,
    "calculations_accurate": true,
    "final_answer_correct": false,
    "feedback": "Excellent approach and calculations, but check the final answer",
    "step_by_step_assessment": ["Step 1: Correct", "Step 2: Correct", "Step 3: Error in calculation"],
    "suggestions": "Review the arithmetic in the final step"
}}
""",
            'general': """
Grade this student response based on the assignment criteria.

Assignment: {question}
Student Response: {response}
Grading Criteria: {criteria}

Provide comprehensive feedback and scoring.

Format as JSON:
{{
    "score": 85,
    "max_points": 100,
    "percentage": 85,
    "feedback": "Overall assessment of the response",
    "criteria_scores": {{
        "understanding": 20,
        "application": 18,
        "communication": 22
    }},
    "suggestions": "Specific recommendations for improvement"
}}
"""
        }
    
    def safe_log(self, level, message):
        """Safely log messages whether we have Flask context or not"""
        try:
            if level == 'info':
                current_app.logger.info(message)
            elif level == 'error':
                current_app.logger.error(message)
            else:
                current_app.logger.debug(message)
        except:
            # Fallback to print if no Flask context
            print(f"[{level.upper()}] {message}")
    
    def init_ai(self):
        """Initialize the Gemini AI model"""
        try:
            if not GENAI_AVAILABLE or genai is None:
                print("ERROR: Google Generative AI library not available")
                return False
                
            # Try multiple ways to get the API key
            api_key = None
            try:
                api_key = current_app.config.get('GEMINI_API_KEY') or current_app.config.get('GOOGLE_AI_API_KEY')
            except:
                # Fallback to environment variables if no Flask context
                import os
                api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_AI_API_KEY')
            
            if not api_key:
                print("ERROR: GEMINI_API_KEY or GOOGLE_AI_API_KEY not configured")
                return False
            
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')  # Use available model
            print("[SUCCESS] Auto-Grading AI initialized successfully")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to initialize AI for grading: {e}")
            return False
    
    def grade_assignment(self, assignment_type, question, student_response, answer_key=None, criteria=None, max_points=100):
        """
        Grade a student assignment using AI
        
        Args:
            assignment_type: 'essay', 'short_answer', 'math_problem', 'general'
            question: The assignment question/prompt
            student_response: Student's submitted answer
            answer_key: Expected answer or key points (optional)
            criteria: Grading criteria (optional)
            max_points: Maximum points for the assignment
        
        Returns:
            dict: Grading results with score, feedback, and suggestions
        """
        if not self.model and not self.init_ai():
            return {
                "error": "AI grading service unavailable",
                "score": 0,
                "feedback": "Unable to grade automatically. Please grade manually.",
                "success": False
            }
        
        try:
            # Select appropriate prompt based on assignment type
            prompt_template = self.grading_prompts.get(assignment_type, self.grading_prompts['general'])
            
            # Format the prompt with assignment details
            prompt = prompt_template.format(
                question=question,
                response=student_response,
                answer_key=answer_key or "No answer key provided",
                criteria=criteria or "Standard academic criteria",
                max_points=max_points
            )
            
            # Generate AI response
            response = self.model.generate_content(prompt)
            
            # Parse JSON response
            result = self._parse_grading_response(response.text)
            
            # Add metadata
            result['graded_at'] = datetime.now().isoformat()
            result['assignment_type'] = assignment_type
            result['ai_graded'] = True
            result['success'] = True
            
            return result
            
        except Exception as e:
            self.safe_log('error', f"Error in AI grading: {e}")
            return {
                "error": f"Grading failed: {str(e)}",
                "score": 0,
                "feedback": "Unable to grade automatically. Please grade manually.",
                "ai_graded": False,
                "success": False
            }
    
    def _parse_grading_response(self, ai_response):
        """Parse AI response and extract JSON grading data"""
        try:
            # Try to find JSON in the response
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
            else:
                # Fallback: create basic response from text
                return {
                    "score": 70,  # Default score
                    "feedback": ai_response,
                    "ai_graded": True,
                    "parsing_note": "Response parsed as text (JSON parsing failed)"
                }
        except json.JSONDecodeError:
            # If JSON parsing fails, return the raw response
            return {
                "score": 70,  # Default score
                "feedback": ai_response,
                "ai_graded": True,
                "parsing_note": "Unable to parse JSON response"
            }
    
    def grade_multiple_choice(self, question, correct_answer, student_answer, explanations=None):
        """Grade multiple choice questions"""
        is_correct = str(student_answer).strip().lower() == str(correct_answer).strip().lower()
        
        result = {
            "score": 100 if is_correct else 0,
            "max_points": 100,
            "correct": is_correct,
            "correct_answer": correct_answer,
            "student_answer": student_answer,
            "feedback": "Correct!" if is_correct else f"Incorrect. The correct answer is {correct_answer}.",
            "ai_graded": False  # This is rule-based, not AI
        }
        
        if explanations and correct_answer in explanations:
            result["explanation"] = explanations[correct_answer]
        
        return result
    
    def batch_grade_assignments(self, assignments_data):
        """Grade multiple assignments in batch"""
        results = []
        
        for assignment in assignments_data:
            result = self.grade_assignment(
                assignment_type=assignment.get('type', 'general'),
                question=assignment['question'],
                student_response=assignment['response'],
                answer_key=assignment.get('answer_key'),
                criteria=assignment.get('criteria'),
                max_points=assignment.get('max_points', 100)
            )
            
            result['assignment_id'] = assignment.get('id')
            result['student_id'] = assignment.get('student_id')
            results.append(result)
        
        return results
    
    def provide_improvement_suggestions(self, grading_history):
        """Analyze grading history and provide learning suggestions"""
        if not self.model and not self.init_ai():
            return {"error": "AI service unavailable"}
        
        prompt = f"""
Analyze this student's grading history and provide personalized learning suggestions:

Grading History: {json.dumps(grading_history, indent=2)}

Provide recommendations for:
1. Strengths to build on
2. Areas needing improvement
3. Specific study strategies
4. Resources that might help

Format as JSON:
{{
    "overall_performance": "analysis",
    "strengths": ["strength 1", "strength 2"],
    "improvement_areas": ["area 1", "area 2"],
    "study_strategies": ["strategy 1", "strategy 2"],
    "recommended_resources": ["resource 1", "resource 2"],
    "next_steps": "specific next actions"
}}
"""
        
        try:
            response = self.model.generate_content(prompt)
            return self._parse_grading_response(response.text)
        except Exception as e:
            return {"error": f"Failed to generate suggestions: {str(e)}"}

# Global instance
auto_grading_service = AutoGradingService()