try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Google Generative AI not available: {e}")
    genai = None
    GENAI_AVAILABLE = False

from flask import current_app
import json
import re
import PyPDF2
import io
from datetime import datetime

class ContentGenerationService:
    def __init__(self):
        self.model = None
        self.generation_prompts = {
            'quiz_questions': """
Based on the following document content, generate {num_questions} quiz questions of type "{question_type}".

Document Content:
{content}

Please create diverse, educational questions that test understanding of key concepts.

For multiple choice questions, provide 4 options (A, B, C, D) with one correct answer.
For short answer questions, provide the question and expected answer.
For essay questions, provide the question and key points to address.

Format as JSON:
{{
    "questions": [
        {{
            "type": "multiple_choice",
            "question": "What is the main concept discussed?",
            "options": {{
                "A": "Option 1",
                "B": "Option 2", 
                "C": "Option 3",
                "D": "Option 4"
            }},
            "correct_answer": "B",
            "explanation": "Explanation of why B is correct",
            "difficulty": "medium",
            "topic": "Main topic area"
        }}
    ]
}}
""",
            'study_guide': """
Create a comprehensive study guide based on this content:

{content}

Include:
1. Key concepts and definitions
2. Important facts and figures
3. Main themes or topics
4. Study tips and memory aids
5. Practice questions

Format as JSON:
{{
    "title": "Study Guide Title",
    "key_concepts": [
        {{"term": "Concept", "definition": "Definition", "importance": "Why it matters"}}
    ],
    "main_topics": ["Topic 1", "Topic 2"],
    "important_facts": ["Fact 1", "Fact 2"],
    "study_tips": ["Tip 1", "Tip 2"],
    "practice_questions": ["Question 1", "Question 2"]
}}
""",
            'flashcards': """
Generate flashcards from this content for student studying:

{content}

Create {num_cards} flashcards with clear, concise questions and answers.

Format as JSON:
{{
    "flashcards": [
        {{
            "front": "Question or prompt",
            "back": "Answer or explanation",
            "category": "Topic category",
            "difficulty": "easy/medium/hard"
        }}
    ]
}}
""",
            'summary': """
Create a comprehensive summary of this document:

{content}

Provide:
1. Executive summary (2-3 sentences)
2. Main points (bullet points)
3. Key takeaways
4. Important details

Format as JSON:
{{
    "executive_summary": "Brief overview...",
    "main_points": ["Point 1", "Point 2"],
    "key_takeaways": ["Takeaway 1", "Takeaway 2"],
    "important_details": ["Detail 1", "Detail 2"],
    "word_count": 150,
    "reading_time": "2 minutes"
}}
""",
            'lesson_plan': """
Create a lesson plan based on this content:

{content}

Duration: {duration} minutes
Target audience: {audience}

Format as JSON:
{{
    "title": "Lesson Title",
    "duration": "{duration} minutes",
    "objectives": ["Students will be able to...", "Students will understand..."],
    "materials_needed": ["Material 1", "Material 2"],
    "lesson_structure": [
        {{"phase": "Introduction", "duration": "5 min", "activities": ["Activity 1"]}},
        {{"phase": "Main Content", "duration": "20 min", "activities": ["Activity 1", "Activity 2"]}},
        {{"phase": "Conclusion", "duration": "5 min", "activities": ["Summary"]}}
    ],
    "assessment_methods": ["Method 1", "Method 2"],
    "homework_suggestions": ["Task 1", "Task 2"]
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
            # Use the model name from config, or fallback to default
            try:
                model_name = current_app.config.get('GEMINI_MODEL', 'models/gemini-2.5-flash')
            except:
                # Fallback if no Flask context
                import os
                model_name = os.getenv('GEMINI_MODEL', 'models/gemini-2.5-flash')
            
            # Remove 'models/' prefix if present for the actual API call
            if model_name.startswith('models/'):
                model_name = model_name[7:]  # Remove 'models/' prefix
            
            self.model = genai.GenerativeModel(model_name)
            print(f"✅ Content Generation AI initialized successfully with model: {model_name}")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize AI for content generation: {e}")
            return False
    
    def extract_text_from_pdf(self, pdf_file):
        """Extract text content from PDF file"""
        try:
            print("📄 Extracting text from PDF...")
            # Reset file pointer to beginning
            pdf_file.seek(0)
            
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text_content = ""
            
            print(f"📄 PDF has {len(pdf_reader.pages)} pages")
            
            for i, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                text_content += page_text + "\n"
                print(f"📄 Extracted {len(page_text)} characters from page {i+1}")
            
            final_text = text_content.strip()
            print(f"📄 Total extracted text: {len(final_text)} characters")
            
            if len(final_text) < 10:
                print("⚠️ Warning: Very little text extracted from PDF")
                return None
            
            return final_text
        except Exception as e:
            print(f"❌ Error extracting text from PDF: {e}")
            return None

    def extract_text_from_file(self, file):
        """Extract text content from text file"""
        try:
            print("📄 Extracting text from file...")
            # Reset file pointer to beginning
            file.seek(0)
            
            # Read as text
            text_content = file.read()
            
            # Handle bytes vs string
            if isinstance(text_content, bytes):
                text_content = text_content.decode('utf-8', errors='ignore')
            
            final_text = text_content.strip()
            print(f"📄 Total extracted text: {len(final_text)} characters")
            
            if len(final_text) < 10:
                print("⚠️ Warning: Very little text extracted from file")
                return None
            
            return final_text
        except Exception as e:
            print(f"❌ Error extracting text from file: {e}")
            return None
    
    def generate_quiz_questions(self, content, num_questions=5, question_type="mixed"):
        if not GENAI_AVAILABLE:
            return {
                "error": "AI service not available - Google Generative AI library not installed or configured",
                "success": False
            }
        
        if not self.model and not self.init_ai():
            return {"error": "AI service unavailable", "success": False}
        
        try:
            if question_type == "mixed":
                question_type = "a mix of multiple choice, short answer, and essay questions"
            
            prompt = self.generation_prompts['quiz_questions'].format(
                content=content[:4000],
                num_questions=num_questions,
                question_type=question_type
            )
            
            response = self.model.generate_content(prompt)
            result = self._parse_json_response(response.text)
            
            result['generated_at'] = datetime.now().isoformat()
            result['content_type'] = 'quiz_questions'
            result['num_questions_requested'] = num_questions
            result['question_type'] = question_type
            result['success'] = True
            
            return result
            
        except Exception as e:
            try:
                current_app.logger.error(f"Error generating quiz questions: {e}")
            except:
                pass
            
            return {"error": f"Failed to generate quiz questions: {str(e)}", "success": False}
    
    def generate_study_guide(self, content, title="Study Guide"):
        """Generate a study guide from content"""
        if not self.model and not self.init_ai():
            return {"error": "AI service unavailable"}
        
        try:
            prompt = self.generation_prompts['study_guide'].format(
                content=content[:4000]
            )
            
            response = self.model.generate_content(prompt)
            result = self._parse_json_response(response.text)
            
            if 'title' not in result:
                result['title'] = title
            
            result['generated_at'] = datetime.now().isoformat()
            result['content_type'] = 'study_guide'
            
            return result
            
        except Exception as e:
            current_app.logger.error(f"Error generating study guide: {e}")
            return {"error": f"Failed to generate study guide: {str(e)}"}
    
    def generate_flashcards(self, content, num_cards=10):
        """Generate flashcards from content"""
        if not self.model and not self.init_ai():
            return {"error": "AI service unavailable"}
        
        try:
            prompt = self.generation_prompts['flashcards'].format(
                content=content[:4000],
                num_cards=num_cards
            )
            
            response = self.model.generate_content(prompt)
            result = self._parse_json_response(response.text)
            
            result['generated_at'] = datetime.now().isoformat()
            result['content_type'] = 'flashcards'
            result['total_cards'] = len(result.get('flashcards', []))
            
            return result
            
        except Exception as e:
            current_app.logger.error(f"Error generating flashcards: {e}")
            return {"error": f"Failed to generate flashcards: {str(e)}"}
    
    def generate_summary(self, content):
        """Generate a summary of content"""
        if not self.model and not self.init_ai():
            return {"error": "AI service unavailable"}
        
        try:
            prompt = self.generation_prompts['summary'].format(
                content=content[:4000]
            )
            
            response = self.model.generate_content(prompt)
            result = self._parse_json_response(response.text)
            
            result['generated_at'] = datetime.now().isoformat()
            result['content_type'] = 'summary'
            result['original_length'] = len(content.split())
            
            return result
            
        except Exception as e:
            current_app.logger.error(f"Error generating summary: {e}")
            return {"error": f"Failed to generate summary: {str(e)}"}
    
    def generate_lesson_plan(self, content, duration=30, audience="high school students"):
        """Generate a lesson plan from content"""
        if not self.model and not self.init_ai():
            return {"error": "AI service unavailable"}
        
        try:
            prompt = self.generation_prompts['lesson_plan'].format(
                content=content[:4000],
                duration=duration,
                audience=audience
            )
            
            response = self.model.generate_content(prompt)
            result = self._parse_json_response(response.text)
            
            result['generated_at'] = datetime.now().isoformat()
            result['content_type'] = 'lesson_plan'
            result['target_audience'] = audience
            
            return result
            
        except Exception as e:
            current_app.logger.error(f"Error generating lesson plan: {e}")
            return {"error": f"Failed to generate lesson plan: {str(e)}"}
    
    def generate_from_pdf(self, pdf_file, content_type="quiz_questions", **kwargs):
        """Generate content from PDF or text file"""
        try:
            current_app.logger.info(f"Processing file for content generation")
            
            # Check if AI is available
            if not GENAI_AVAILABLE:
                current_app.logger.error("Google Generative AI not available")
                return {
                    "error": "AI service not available. Please check server configuration.",
                    "success": False,
                    "fallback": "Content generation requires Google Generative AI library"
                }
            
            # Determine file type and extract text accordingly
            filename = getattr(pdf_file, 'filename', 'unknown')
            current_app.logger.info(f"Filename: {filename}")
            
            if filename.lower().endswith('.pdf'):
                # Handle PDF files
                text_content = self.extract_text_from_pdf(pdf_file)
                if not text_content:
                    return {"error": "Could not extract text from PDF", "success": False}
            else:
                # Handle text files (txt, docx, etc.)
                text_content = self.extract_text_from_file(pdf_file)
                if not text_content:
                    return {"error": "Could not extract text from file", "success": False}
            
            current_app.logger.info(f"Extracted {len(text_content)} characters from file")
            
            # Generate content based on type
            if content_type == "quiz_questions":
                result = self.generate_quiz_questions(
                    text_content, 
                    kwargs.get('num_questions', 5),
                    kwargs.get('question_type', 'mixed')
                )
            elif content_type == "study_guide":
                result = self.generate_study_guide(text_content, kwargs.get('title', 'Study Guide'))
            elif content_type == "flashcards":
                result = self.generate_flashcards(text_content, kwargs.get('num_cards', 10))
            elif content_type == "summary":
                result = self.generate_summary(text_content)
            elif content_type == "lesson_plan":
                result = self.generate_lesson_plan(
                    text_content,
                    kwargs.get('duration', 30),
                    kwargs.get('audience', 'high school students')
                )
            else:
                return {"error": f"Unknown content type: {content_type}", "success": False}
            
            # Ensure result has success flag
            if isinstance(result, dict) and 'success' not in result:
                if 'error' in result:
                    result['success'] = False
                else:
                    result['success'] = True
            
            return result
                
        except Exception as e:
            try:
                current_app.logger.error(f"Error in generate_from_pdf: {e}")
                current_app.logger.error(f"Error type: {type(e).__name__}")
                import traceback
                current_app.logger.error(f"Traceback: {traceback.format_exc()}")
            except:
                print(f"❌ Error in generate_from_pdf: {e}")
                import traceback
                traceback.print_exc()
            
            return {
                "error": f"Failed to generate content: {str(e)}", 
                "success": False,
                "error_type": type(e).__name__
            }
    
    def generate_practice_problems(self, subject, topic, difficulty="medium", num_problems=5):
        """Generate practice problems for a specific subject and topic"""
        if not self.model and not self.init_ai():
            return {"error": "AI service unavailable"}
        
        prompt = f"""
Generate {num_problems} practice problems for {subject} on the topic of {topic}.
Difficulty level: {difficulty}

For each problem, provide:
1. The problem statement
2. Step-by-step solution
3. Final answer
4. Learning objective

Format as JSON:
{{
    "problems": [
        {{
            "problem_number": 1,
            "statement": "Problem statement here",
            "solution_steps": ["Step 1", "Step 2", "Step 3"],
            "final_answer": "Answer",
            "learning_objective": "What this problem teaches",
            "difficulty": "{difficulty}",
            "estimated_time": "5 minutes"
        }}
    ],
    "subject": "{subject}",
    "topic": "{topic}"
}}
"""
        
        try:
            response = self.model.generate_content(prompt)
            result = self._parse_json_response(response.text)
            
            result['generated_at'] = datetime.now().isoformat()
            result['content_type'] = 'practice_problems'
            
            return result
            
        except Exception as e:
            current_app.logger.error(f"Error generating practice problems: {e}")
            return {"error": f"Failed to generate practice problems: {str(e)}"}
    
    def enhance_content_with_examples(self, content, num_examples=3):
        """Enhance content by adding relevant examples"""
        if not self.model and not self.init_ai():
            return {"error": "AI service unavailable"}
        
        prompt = f"""
Analyze this content and add {num_examples} relevant, concrete examples to illustrate the concepts:

{content[:3000]}

For each major concept, provide practical examples that help students understand.

Format as JSON:
{{
    "enhanced_content": "Original content with examples integrated",
    "examples_added": [
        {{
            "concept": "Concept name",
            "example": "Practical example",
            "explanation": "Why this example helps"
        }}
    ],
    "improvement_notes": "How the examples enhance understanding"
}}
"""
        
        try:
            response = self.model.generate_content(prompt)
            result = self._parse_json_response(response.text)
            
            result['generated_at'] = datetime.now().isoformat()
            result['content_type'] = 'enhanced_content'
            
            return result
            
        except Exception as e:
            current_app.logger.error(f"Error enhancing content: {e}")
            return {"error": f"Failed to enhance content: {str(e)}"}
    
    def _parse_json_response(self, ai_response):
        """Parse AI response and extract JSON data"""
        try:
            # Try to find JSON in the response
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
            else:
                # Fallback: create basic response from text
                return {
                    "content": ai_response,
                    "parsing_note": "Response parsed as text (JSON parsing failed)"
                }
        except json.JSONDecodeError:
            # If JSON parsing fails, return the raw response
            return {
                "content": ai_response,
                "parsing_note": "Unable to parse JSON response"
            }
    
    def _generate_content_with_ai(self, content, content_type, num_questions=10, difficulty="intermediate"):
        """Generate content using AI based on content type"""
        try:
            print(f"🤖 Generating {content_type} with Gemini...")
            
            # Map content type to generation method
            if content_type == "quiz" or content_type == "quiz_questions":
                return self.generate_quiz_questions(content, num_questions, "multiple_choice")
            elif content_type == "study_guide":
                return self.generate_study_guide(content)
            elif content_type == "summary":
                return self.generate_summary(content)
            elif content_type == "flashcards":
                return self.generate_flashcards(content, num_questions)
            else:
                # Default to quiz generation
                return self.generate_quiz_questions(content, num_questions, "multiple_choice")
                
        except Exception as e:
            print(f"❌ Error in _generate_content_with_ai: {e}")
            return {"error": str(e)}
    
    def generate_from_text(self, text, content_type="quiz_questions", num_questions=10, difficulty="intermediate"):
        """Generate content from plain text input"""
        try:
            print(f"Generating {content_type} from text (Gemini 2.5 Flash)")
            
            if not text.strip():
                return {"success": False, "error": "No text content provided"}
            
            # Initialize model if needed
            if not self.model:
                if not self.init_ai():
                    return {"success": False, "error": "Failed to initialize AI model"}
            
            # Generate content using the same logic as PDF processing
            result = self._generate_content_with_ai(text, content_type, num_questions, difficulty)
            
            # Check if result contains an error
            if result and "error" in result:
                return {
                    "success": False,
                    "error": result["error"]
                }
            elif result:
                # Format the response properly
                if isinstance(result, dict) and "content" in result:
                    formatted_content = result["content"]
                else:
                    formatted_content = str(result)
                
                return {
                    "success": True,
                    "content": formatted_content,
                    "content_type": content_type,
                    "generated_at": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to generate content from text"
                }
                
        except Exception as e:
            print(f"Error generating content from text: {e}")
            return {
                "success": False,
                "error": f"Content generation failed: {str(e)}"
            }

# Global instance
content_generation_service = ContentGenerationService()