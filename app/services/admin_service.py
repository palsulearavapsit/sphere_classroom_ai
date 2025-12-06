from ..db import get_db
from passlib.hash import pbkdf2_sha256

def list_users():
    db = get_db()
    rows = db.execute("SELECT id,email,role,full_name,created_at FROM users ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]

def create_user(data):
    """Create a new user with validation"""
    try:
        # Validation
        email = data.get("email", "").strip()
        password = data.get("password", "").strip()
        role = data.get("role", "").strip()
        full_name = data.get("full_name", "").strip()
        
        if not email or not password or not role or not full_name:
            return {"success": False, "error": "All fields are required"}
        
        if role not in ["student", "teacher", "admin"]:
            return {"success": False, "error": "Invalid role"}
        
        if len(password) < 6:
            return {"success": False, "error": "Password must be at least 6 characters"}
        
        db = get_db()
        
        # Check if email already exists
        existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            return {"success": False, "error": "Email already exists"}
        
        # Create user
        db.execute("INSERT INTO users(email,password_hash,role,full_name) VALUES(?,?,?,?)",
                   (email, pbkdf2_sha256.hash(password), role, full_name))
        db.commit()
        
        return {"success": True, "message": "User created successfully"}
        
    except Exception as e:
        return {"success": False, "error": f"Database error: {str(e)}"}

def update_user(data):
    db = get_db()
    fields, params = [], []
    if "email" in data: fields.append("email=?"); params.append(data["email"])
    if "role" in data: fields.append("role=?"); params.append(data["role"])
    if "full_name" in data: fields.append("full_name=?"); params.append(data["full_name"])
    if "password" in data and data["password"]:
        fields.append("password_hash=?"); params.append(pbkdf2_sha256.hash(data["password"]))
    params.append(data["id"])
    db.execute(f"UPDATE users SET {', '.join(fields)} WHERE id=?", params)
    db.commit()
    return {"ok": True}

def delete_user(user_id):
    """Delete a user with enhanced validation and protection"""
    try:
        db = get_db()
        
        # Get user details
        user = db.execute("SELECT id, email, role FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            return False
        
        # Strict admin protection - never allow admin deletion
        if user['role'] == 'admin':
            return False
            
        # Additional protection for main admin accounts
        protected_emails = ['admin@ai.com', 'admin@admin.com', 'administrator@ai.com']
        if user['email'].lower() in protected_emails:
            return False
        
        # Check if this would be the last admin (extra safety)
        admin_count = db.execute("SELECT COUNT(*) as count FROM users WHERE role = 'admin'").fetchone()['count']
        if user['role'] == 'admin' and admin_count <= 1:
            return False
        
        # Clean up related data before deleting user
        # Delete user's submissions
        db.execute("DELETE FROM submissions WHERE user_id = ?", (user_id,))
        
        # Remove from enrollments  
        db.execute("DELETE FROM enrollments WHERE user_id = ?", (user_id,))
        
        # Delete classrooms created by this user (if teacher)
        if user['role'] == 'teacher':
            classroom_ids = db.execute("SELECT id FROM classrooms WHERE created_by = ?", (user_id,)).fetchall()
            for classroom in classroom_ids:
                # Remove enrollments in these classrooms
                db.execute("DELETE FROM enrollments WHERE classroom_id = ?", (classroom['id'],))
                # Delete assignments in these classrooms
                db.execute("DELETE FROM assignments WHERE classroom_id = ?", (classroom['id'],))
            # Delete the classrooms
            db.execute("DELETE FROM classrooms WHERE created_by = ?", (user_id,))
        
        # Delete OCR extractions
        db.execute("DELETE FROM ocr_extractions WHERE user_id = ?", (user_id,))
        
        # Delete tutor sessions
        db.execute("DELETE FROM tutor_sessions WHERE user_id = ?", (user_id,))
        
        # Finally delete the user
        db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        db.commit()
        
        return True
        
    except Exception as e:
        print(f"Error deleting user: {e}")  # For debugging
        return False

def db_status():
    db = get_db()
    u = db.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
    c = db.execute("SELECT COUNT(*) c FROM classrooms").fetchone()["c"]
    return {"users": u, "classrooms": c}
