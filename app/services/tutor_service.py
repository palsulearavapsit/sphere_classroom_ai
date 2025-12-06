import os, json
from datetime import datetime
from flask import current_app
from ..db import get_db
from ..ai.gemini_client import ask_gemini

# Import RAG functionality and MySQL data service with graceful fallback
RAG_AVAILABLE = False
def search_documents(q, namespace="default"):
    return {"results": [], "mode": "unavailable"}

try:
    from app.services.mysql_data_service import mysql_data_service
    MYSQL_AVAILABLE = True  # Re-enabled for admin functionality
except ImportError as e:
    print(f"MySQL service not available: {e}")
    MYSQL_AVAILABLE = False
    class MockMySQLService:
        def search_data_context(self, query, limit=5):
            return "MySQL service not configured"
    mysql_data_service = MockMySQLService()

# Import OCR data service
try:
    from app.services.ocr_data_service import search_ocr_text, get_recent_ocr_context
    OCR_DATA_AVAILABLE = True
except ImportError as e:
    print(f"OCR data service not available: {e}")
    OCR_DATA_AVAILABLE = False
    def search_ocr_text(user_id, query, limit=10):
        return []
    def get_recent_ocr_context(user_id, max_chars=2000):
        return ""

def get_subject_context(message):
    """Determine the academic subject and provide specialized context"""
    subjects = {
        'math': ['math', 'mathematics', 'algebra', 'calculus', 'geometry', 'trigonometry', 'equation', 'solve', 'formula'],
        'science': ['science', 'physics', 'chemistry', 'biology', 'experiment', 'molecule', 'atom', 'cell', 'energy'],
        'english': ['english', 'literature', 'writing', 'essay', 'grammar', 'poem', 'story', 'analysis'],
        'history': ['history', 'historical', 'war', 'ancient', 'civilization', 'revolution', 'empire', 'century'],
        'programming': ['code', 'programming', 'python', 'javascript', 'algorithm', 'function', 'variable', 'debug']
    }
    
    message_lower = message.lower()
    detected_subjects = []
    
    for subject, keywords in subjects.items():
        if any(keyword in message_lower for keyword in keywords):
            detected_subjects.append(subject)
    
    return detected_subjects

def get_difficulty_level(message, user_id):
    """Analyze the complexity of the question to adjust response difficulty"""
    db = get_db()
    
    # Check user's previous interactions for difficulty patterns
    try:
        user_sessions = db.execute(
            "SELECT messages_json FROM tutor_sessions WHERE user_id=? ORDER BY created_at DESC LIMIT 5", 
            (user_id,)
        ).fetchall()
        
        total_messages = 0
        complex_indicators = 0
        
        for session in user_sessions:
            messages = json.loads(session["messages_json"] or "[]")
            for msg in messages:
                if msg["role"] == "user":
                    total_messages += 1
                    # Check for complexity indicators
                    content = msg["content"].lower()
                    if any(word in content for word in ['explain', 'analyze', 'compare', 'evaluate', 'prove', 'derive']):
                        complex_indicators += 1
        
        if total_messages > 0:
            complexity_ratio = complex_indicators / total_messages
            if complexity_ratio > 0.6:
                return 'advanced'
            elif complexity_ratio > 0.3:
                return 'intermediate'
        
    except Exception as e:
        current_app.logger.error(f"Error analyzing difficulty: {e}")
    
    # Fallback to analyzing current message
    message_lower = message.lower()
    advanced_keywords = ['prove', 'derive', 'analyze', 'evaluate', 'synthesis', 'complex', 'advanced']
    basic_keywords = ['what is', 'how to', 'simple', 'basic', 'explain']
    
    if any(keyword in message_lower for keyword in advanced_keywords):
        return 'advanced'
    elif any(keyword in message_lower for keyword in basic_keywords):
        return 'basic'
    else:
        return 'intermediate'

def generate_step_by_step_explanation(message, subject):
    """Generate structured step-by-step explanations for problem-solving"""
    if 'math' in subject:
        return """
Please provide a step-by-step solution following this structure:
1. **Identify**: What type of problem is this?
2. **Given**: What information do we have?
3. **Find**: What are we trying to solve for?
4. **Method**: What approach/formula should we use?
5. **Solution**: Work through the problem step by step
6. **Check**: Verify the answer makes sense
7. **Practice**: Suggest similar problems for practice
"""
    elif 'science' in subject:
        return """
Please structure your explanation using the scientific method:
1. **Observation**: What phenomenon are we studying?
2. **Background**: Relevant scientific principles
3. **Explanation**: How does this work?
4. **Examples**: Real-world applications
5. **Connections**: How this relates to other concepts
6. **Practice**: Questions to test understanding
"""
    elif 'english' in subject:
        return """
Please provide a literary analysis structure:
1. **Context**: Background information
2. **Analysis**: Break down the main elements
3. **Evidence**: Specific examples from the text
4. **Interpretation**: What does this mean?
5. **Connections**: How this relates to themes/other works
6. **Practice**: Writing exercises or discussion questions
"""
    else:
        return """
Please structure your explanation clearly:
1. **Overview**: Brief summary of the topic
2. **Key Concepts**: Main ideas to understand
3. **Detailed Explanation**: Step-by-step breakdown
4. **Examples**: Practical illustrations
5. **Summary**: Key takeaways
6. **Next Steps**: How to continue learning
"""

def get_personalized_learning_suggestions(user_id, current_topic):
    """Generate personalized learning suggestions based on user history"""
    db = get_db()
    
    try:
        # Analyze user's learning patterns
        sessions = db.execute(
            "SELECT messages_json, created_at FROM tutor_sessions WHERE user_id=? ORDER BY created_at DESC LIMIT 10", 
            (user_id,)
        ).fetchall()
        
        topics_discussed = []
        question_types = []
        
        for session in sessions:
            messages = json.loads(session["messages_json"] or "[]")
            for msg in messages:
                if msg["role"] == "user":
                    content = msg["content"].lower()
                    subjects = get_subject_context(content)
                    topics_discussed.extend(subjects)
                    
                    # Categorize question types
                    if any(word in content for word in ['how', 'explain', 'what']):
                        question_types.append('conceptual')
                    elif any(word in content for word in ['solve', 'calculate', 'find']):
                        question_types.append('problem_solving')
                    elif any(word in content for word in ['why', 'analyze', 'compare']):
                        question_types.append('analytical')
        
        # Generate suggestions based on patterns
        suggestions = []
        
        # Subject-based suggestions
        most_common_subjects = list(set(topics_discussed))
        if most_common_subjects:
            suggestions.append(f"Continue exploring {', '.join(most_common_subjects[:2])} topics")
        
        # Question type suggestions
        if 'problem_solving' in question_types:
            suggestions.append("Try more practice problems to strengthen problem-solving skills")
        if 'conceptual' in question_types:
            suggestions.append("Explore deeper conceptual connections between topics")
        
        # Topic connections
        if 'math' in topics_discussed and 'science' in topics_discussed:
            suggestions.append("Explore mathematical applications in physics and chemistry")
        
        return suggestions[:3]  # Return top 3 suggestions
        
    except Exception as e:
        current_app.logger.error(f"Error generating suggestions: {e}")
        return ["Keep asking questions to improve understanding", "Try different types of problems", "Explore related topics"]

def list_sessions(user_id:int):
    db = get_db()
    rows = db.execute("SELECT id,title,created_at FROM tutor_sessions WHERE user_id=? ORDER BY created_at DESC", (user_id,)).fetchall()
    return [dict(r) for r in rows]

def save_session(user_id:int, title:str):
    db = get_db()
    db.execute("INSERT INTO tutor_sessions(user_id,title,messages_json) VALUES(?,?,?)", (user_id, title, "[]"))
    db.commit()
    sid = db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    return sid

def chat_with_tutor(user_id:int, message:str):
    if not message:
        return "Please enter a question.", None
    
    db = get_db()
    # get or create a session
    row = db.execute("SELECT id,messages_json FROM tutor_sessions WHERE user_id=? ORDER BY created_at DESC LIMIT 1", (user_id,)).fetchone()
    if not row:
        sid = save_session(user_id, "New Session")
        messages = []
    else:
        sid = row["id"]
        messages = json.loads(row["messages_json"] or "[]")
    
    messages.append({"role":"user","content":message,"ts":datetime.utcnow().isoformat()})

    # Enhanced AI Tutoring Features
    detected_subjects = get_subject_context(message)
    difficulty_level = get_difficulty_level(message, user_id)
    learning_suggestions = get_personalized_learning_suggestions(user_id, detected_subjects)
    
    # Enhanced context: Search for relevant context from OCR extractions and database
    context_info = ""
    ocr_context = ""
    mysql_context = ""
    
    try:
        # Search OCR extracted text for relevant content
        if OCR_DATA_AVAILABLE:
            # First try targeted search for specific query terms
            ocr_search_results = search_ocr_text(user_id, message, limit=5)
            if ocr_search_results:
                ocr_chunks = []
                for i, result in enumerate(ocr_search_results[:3]):
                    # Truncate long text but keep relevant parts
                    text_preview = result['text'][:400] + "..." if len(result['text']) > 400 else result['text']
                    created_at = result['created_at']
                    if isinstance(created_at, str):
                        date_part = created_at[:10]
                    else:
                        date_part = str(created_at)[:10]
                    ocr_chunks.append(f"OCR Extract {i+1} (from {date_part}):\n{text_preview}")
                
                ocr_context = "\n\n".join(ocr_chunks)
            else:
                # If no specific matches, get recent OCR context
                ocr_context = get_recent_ocr_context(user_id, max_chars=1000)
            
            # Add OCR context to overall context
            if ocr_context:
                context_info = f"=== OCR EXTRACTED TEXT ===\n{ocr_context}"
        
        # Search MySQL database for relevant data (disabled for now)
        if MYSQL_AVAILABLE:
            mysql_context = mysql_data_service.search_data_context(message, limit=5)
            if mysql_context and mysql_context != "No relevant data found in database.":
                if context_info:
                    context_info += f"\n\n=== DATABASE CONTEXT ===\n{mysql_context}"
                else:
                    context_info = f"=== DATABASE CONTEXT ===\n{mysql_context}"
                    
    except Exception as e:
        print(f"Context search error: {e}")
        current_app.logger.error(f"Context search error: {e}")
    
    # Build enhanced AI tutor prompt
    tutor_personality = """You are SPHERE AI, an advanced educational tutor with expertise across all academic subjects. Your teaching philosophy focuses on:

* **Adaptive Learning**: Adjust explanations based on student's level
* **Subject Expertise**: Provide specialized knowledge for each field
* **Step-by-Step Guidance**: Break down complex problems systematically
* **Conceptual Understanding**: Focus on 'why' not just 'how'
* **Encouragement**: Maintain positive, supportive tone
* **Connections**: Show relationships between concepts"""

    subject_guidance = ""
    if detected_subjects:
        subject_guidance = f"\n\n**SUBJECT FOCUS**: This question relates to {', '.join(detected_subjects)}."
        for subject in detected_subjects:
            if subject in ['math', 'science', 'english']:
                subject_guidance += f"\n{generate_step_by_step_explanation(message, detected_subjects)}"
                break

    difficulty_guidance = f"\n\n**DIFFICULTY LEVEL**: {difficulty_level.title()}"
    if difficulty_level == 'basic':
        difficulty_guidance += " - Use simple language, provide definitions, include basic examples"
    elif difficulty_level == 'intermediate':
        difficulty_guidance += " - Balance detail with clarity, connect to previous knowledge"
    elif difficulty_level == 'advanced':
        difficulty_guidance += " - Provide in-depth analysis, encourage critical thinking, discuss nuances"

    personalization = ""
    if learning_suggestions:
        personalization = f"\n\n**PERSONALIZED SUGGESTIONS**:\n" + "\n".join([f"- {suggestion}" for suggestion in learning_suggestions])

    # Enhanced prompt with all AI tutoring features
    if context_info:
        enhanced_message = f"""{tutor_personality}

{context_info}

{subject_guidance}

{difficulty_guidance}

{personalization}

**STUDENT QUESTION**: {message}

Please provide a comprehensive, educational response that:
1. Directly answers the student's question
2. Uses appropriate difficulty level for this learner
3. Incorporates relevant context when available
4. Provides step-by-step guidance if applicable
5. Encourages further learning with related questions
6. Uses the specialized approach for the detected subject area

Format your response with clear sections and use educational emojis to make it engaging."""
    else:
        enhanced_message = f"""{tutor_personality}

{subject_guidance}

{difficulty_guidance}

{personalization}

**STUDENT QUESTION**: {message}

Please provide a comprehensive, educational response following the guidelines above."""

    # Call Gemini with enhanced prompt
    reply = ask_gemini(enhanced_message, messages[:-1])  # Don't include current message in history
    
    # Add AI tutoring enhancements info
    enhancements_used = []
    if detected_subjects:
        enhancements_used.append(f"Subject-specific guidance for {', '.join(detected_subjects)}")
    if difficulty_level != 'intermediate':
        enhancements_used.append(f"{difficulty_level.title()}-level explanations")
    if learning_suggestions:
        enhancements_used.append("Personalized learning suggestions")
    
    # Add context info to reply if OCR or database was used
    context_sources = []
    if context_info:
        has_db = MYSQL_AVAILABLE and bool(mysql_context and mysql_context != "No relevant data found in database." and mysql_context != "MySQL service not configured")
        has_ocr = OCR_DATA_AVAILABLE and bool(ocr_context)
        
        if has_db:
            context_sources.append("database information")
        if has_ocr:
            context_sources.append("OCR-extracted text")

    footer_info = []
    if context_sources:
        sources_text = " and ".join(context_sources)
        footer_info.append(f"Enhanced with {sources_text}")
    
    if enhancements_used:
        footer_info.append(f"AI Features: {', '.join(enhancements_used)}")
    
    if footer_info:
        reply += f"\n\n---\n*{' | '.join(footer_info)}*"

    messages.append({
        "role":"assistant",
        "content":reply,
        "ts":datetime.utcnow().isoformat(), 
        "context_used": bool(context_info),
        "subjects": detected_subjects,
        "difficulty": difficulty_level,
        "enhancements": enhancements_used
    })
    
    db.execute("UPDATE tutor_sessions SET messages_json=? WHERE id=?", (json.dumps(messages), sid))
    db.commit()
    
    return reply, {
        "id": sid, 
        "messages": messages, 
        "ocr_context_used": bool(ocr_context),
        "subjects_detected": detected_subjects,
        "difficulty_level": difficulty_level,
        "personalized_suggestions": learning_suggestions
    }
