# ai_tutor.py
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# Global Client and Model
try:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    MODEL_NAME = "gemini-2.5-flash"
except Exception as e:
    print(f"Error initializing Gemini client: {e}")
    client = None # Fallback stub will check this

def create_tutor_session(role):
    """Initializes a new chat session with a system instruction."""
    if not client:
        return None # Return None on failure

    # System instruction for a context-aware tutor
    system_instruction = (
        "You are an expert, context-aware AI Tutor for Physics and STEM education. "
        "Keep your answers concise, pedagogical, and encouraging. "
        "Tailor your response based on the user's role: "
        "- If Student: Provide direct explanations and hints, not full answers. "
        "- If Teacher: Provide detailed explanations, teaching strategies, and resource suggestions."
    )
    
    config = types.GenerateContentConfig(
        system_instruction=system_instruction
    )
    
    return client.chats.create(model=MODEL_NAME, config=config)

def send_message(chat_session, prompt):
    """Sends a message to the Gemini chat and returns the response."""
    if chat_session:
        try:
            response = chat_session.send_message(prompt)
            # Log the message for the project's 'Tutor sessions table' feature
            # In a real app, this would save to a database.
            print(f"Logging session message: User: {prompt[:20]}, AI: {response.text[:20]}") 
            return response.text
        except Exception as e:
            return f"AI Service Error (Gemini): {e}"
    else:
        return "AI Service is unavailable. Please check the API key."
