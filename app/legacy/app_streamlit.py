# app_logic.py
import pandas as pd
import os

# --- Constants & Initialization ---
USER_ROLES = ["student", "teacher", "admin"]
DATASET_PATH = 'data/SPHERE dataset.csv'

# Dummy Database Stubs (In-memory storage)
USERS = {
    "admin@ai.com": {"password_hash": "hashed_admin", "role": "admin", "name": "Admin User"},
    "teacher@ai.com": {"password_hash": "hashed_teacher", "role": "teacher", "name": "Prof. Smith"},
    "student@ai.com": {"password_hash": "hashed_student", "role": "student", "name": "Alice Student"},
}

CLASSROOMS = {
    "PHYS101": {"name": "Introductory Physics", "teacher": "teacher@ai.com", "code": "SPHR25"},
}

ENROLLMENTS = {
    "student@ai.com": ["PHYS101"],
}

# --- Data Merging & Management (Your CSV) ---

def load_sphere_dataset():
    """Loads and merges the SPHERE dataset into the application logic."""
    if os.path.exists(DATASET_PATH):
        try:
            df = pd.read_csv(DATASET_PATH)
            print(f"SPHERE Dataset loaded successfully. Shape: {df.shape}")
            return df
        except Exception as e:
            print(f"Error loading dataset: {e}")
            return pd.DataFrame()
    else:
        print(f"Warning: Dataset not found at {DATASET_PATH}")
        return pd.DataFrame()

SPHERE_DATA = load_sphere_dataset()

# --- Authentication & User Management ---

def authenticate_user(email, password):
    """Authenticates a user (stub for password hashing check)."""
    if email in USERS:
        # NOTE: In a real app, 'password' would be hashed and compared securely.
        # This is a simple stub for demonstration.
        if USERS[email]["password_hash"] == f"hashed_{email.split('@')[0]}":
            return USERS[email]
    return None

def get_user_info(email):
    """Retrieves user info."""
    return USERS.get(email)

# --- Feature Stubs ---

def create_classroom(teacher_email, name):
    """Stub for classroom creation."""
    new_id = f"CLS{len(CLASSROOMS) + 1}"
    CLASSROOMS[new_id] = {"name": name, "teacher": teacher_email, "code": new_id.upper()}
    return new_id

def get_student_assignments(student_email):
    """Stub: Returns a list of assignments."""
    return [{"id": 1, "name": "Kinematics Test", "due": "2025-10-15", "status": "Pending"}]

def get_teacher_analytics(classroom_id):
    """Stub: Returns analytics data (e.g., test scores)."""
    return {
        "avg_score": 85.5,
        "completion_rate": 0.92,
        "top_student": "Alice Student"
    }

def process_ocr_upload(image_data):
    """Stub for OCR processing logic (Tesseract/Pillow integration)."""
    # In a real app, this would call Tesseract to extract text
    return "Extracted Text:\n$F = ma$\nExperiment Data: (1, 10), (2, 21)"
