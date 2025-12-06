import os
from flask import current_app


try:
    import google.generativeai as genai
except Exception:
    genai = None

def ask_gemini(prompt:str, context_messages=None)->str:
    api_key = current_app.config.get("GEMINI_API_KEY","")
    model_name = current_app.config.get("GEMINI_MODEL","models/gemini-2.5-flash")
    if not api_key or genai is None:
        return "AI is not configured. Please set GEMINI_API_KEY."
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    # basic context join
    sys_context = ""
    if context_messages:
        for m in context_messages[-8:]:
            if m.get("role")=="user":
                sys_context += f"User: {m.get('content')}\n"
            else:
                sys_context += f"Assistant: {m.get('content')}\n"
    prompt_full = f"Context:\n{sys_context}\n\nQuestion:\n{prompt}\n"
    resp = model.generate_content(prompt_full)
    try:
        response_text = resp.text.strip()
        # Replace common problematic Unicode characters for Windows console
        unicode_replacements = {
            '👋': 'Hello',
            '🎯': '*',
            '📚': '[Book]',
            '💡': '[Tip]',
            '🔍': '[Search]',
            '✅': '[OK]',
            '❌': '[Error]',
            '🌟': '*',
            '🔗': '[Link]',
            '•': '-',
            '→': '->',
            '←': '<-',
            '↑': '^',
            '↓': 'v'
        }
        
        for unicode_char, replacement in unicode_replacements.items():
            response_text = response_text.replace(unicode_char, replacement)
            
        return response_text
    except Exception:
        return "AI response error."
