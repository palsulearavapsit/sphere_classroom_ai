"""Service for retrieving and managing OCR extracted data."""

import json
from ..db import get_db
from flask import current_app

def get_user_ocr_extractions(user_id, limit=50):
    """Get all OCR extractions for a user."""
    try:
        db = get_db()
        cursor = db.execute("""
            SELECT id, image_path, text, struct_json, created_at 
            FROM ocr_extractions 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        """, (user_id, limit))
        
        extractions = []
        for row in cursor.fetchall():
            try:
                struct_data = json.loads(row[3]) if row[3] else {}
            except:
                struct_data = {}
            
            created_at = row[4]
            if isinstance(created_at, str):
                created_at_str = created_at
            else:
                created_at_str = str(created_at)
                
            extractions.append({
                'id': row[0],
                'image_path': row[1],
                'text': row[2],
                'struct': struct_data,
                'created_at': created_at_str
            })
        
        return extractions
    except Exception as e:
        current_app.logger.error(f"Error retrieving OCR extractions: {e}")
        return []

def search_ocr_text(user_id, query, limit=10):
    """Search OCR extracted text for relevant content."""
    try:
        db = get_db()
        # Use LIKE for text search (SQLite compatible)
        search_pattern = f"%{query}%"
        cursor = db.execute("""
            SELECT id, image_path, text, created_at 
            FROM ocr_extractions 
            WHERE user_id = ? AND text LIKE ? 
            ORDER BY created_at DESC 
            LIMIT ?
        """, (user_id, search_pattern, limit))
        
        results = []
        for row in cursor.fetchall():
            created_at = row[3]
            if isinstance(created_at, str):
                created_at_str = created_at
            else:
                created_at_str = str(created_at)
                
            results.append({
                'id': row[0],
                'image_path': row[1],
                'text': row[2],
                'created_at': created_at_str,
                'relevance': 'text_match'
            })
        
        return results
    except Exception as e:
        current_app.logger.error(f"Error searching OCR text: {e}")
        return []

def get_recent_ocr_context(user_id, max_chars=2000):
    """Get recent OCR extractions as context for the chatbot."""
    try:
        extractions = get_user_ocr_extractions(user_id, limit=10)
        
        if not extractions:
            return ""
        
        context_parts = []
        total_chars = 0
        
        for extraction in extractions:
            text = extraction['text'].strip()
            if not text or '[OCR' in text:  # Skip errors or empty extractions
                continue
                
            # Add some metadata for context
            created_at = extraction['created_at']
            if isinstance(created_at, str):
                date_str = created_at[:10]  # Just the date part
            else:
                # Handle datetime object
                date_str = str(created_at)[:10]
            context_part = f"[OCR Extract from {date_str}]\n{text}\n"
            
            if total_chars + len(context_part) > max_chars:
                break
                
            context_parts.append(context_part)
            total_chars += len(context_part)
        
        return "\n".join(context_parts)
    except Exception as e:
        current_app.logger.error(f"Error getting OCR context: {e}")
        return ""

def get_all_user_text_content(user_id):
    """Get all text content from user's OCR extractions for comprehensive search."""
    try:
        extractions = get_user_ocr_extractions(user_id, limit=100)
        all_text = []
        
        for extraction in extractions:
            text = extraction['text'].strip()
            if text and '[OCR' not in text:  # Skip errors
                all_text.append(text)
        
        return " ".join(all_text)
    except Exception as e:
        current_app.logger.error(f"Error getting all user text content: {e}")
        return ""