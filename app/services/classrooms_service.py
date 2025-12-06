import secrets, string
from ..db import get_db

def _code(n=6):
    return "".join(secrets.choice(string.ascii_uppercase+string.digits) for _ in range(n))

def create_classroom(name:str, teacher_id:int):
    db = get_db()
    code = _code()
    db.execute("INSERT INTO classrooms(name, join_code, created_by) VALUES(?,?,?)", (name, code, teacher_id))
    db.commit()
    row = db.execute("SELECT last_insert_rowid() as id").fetchone()
    return {"id": row["id"], "name": name, "join_code": code}

def delete_classroom(cid:int, by_id:int):
    db = get_db()
    db.execute("DELETE FROM classrooms WHERE id=?", (cid,))
    db.commit()
    return True

def enroll_with_code(user_id:int, code:str):
    db = get_db()
    row = db.execute("SELECT id FROM classrooms WHERE join_code=?", (code,)).fetchone()
    if not row: return False
    cid = row["id"]
    try:
        db.execute("INSERT INTO enrollments(user_id,classroom_id) VALUES(?,?)",(user_id,cid))
        db.commit()
        return True
    except Exception:
        return True  # already enrolled

def list_enrolled(user_id:int):
    db = get_db()
    rows = db.execute("""
        SELECT c.id,c.name,c.join_code FROM classrooms c
        JOIN enrollments e ON e.classroom_id=c.id WHERE e.user_id=?
        UNION
        SELECT id,name,join_code FROM classrooms WHERE created_by=?
    """,(user_id,user_id)).fetchall()
    return [dict(r) for r in rows]

def list_classrooms_for_teacher(teacher_id:int):
    """Get all classrooms created by a teacher"""
    db = get_db()
    rows = db.execute("""
        SELECT id, name, join_code FROM classrooms 
        WHERE created_by=?
        ORDER BY name
    """, (teacher_id,)).fetchall()
    return [dict(r) for r in rows]

def get_classroom_detail(classroom_id: int, user_id: int):
    """Get detailed classroom information"""
    db = get_db()
    
    # Get classroom info
    classroom = db.execute("""
        SELECT id, name, join_code, created_by, created_at 
        FROM classrooms WHERE id=?
    """, (classroom_id,)).fetchone()
    
    if not classroom:
        return None
    
    classroom = dict(classroom)
    
    # Check if user has access (is creator or enrolled)
    access = db.execute("""
        SELECT 1 FROM classrooms WHERE id=? AND created_by=?
        UNION
        SELECT 1 FROM enrollments WHERE classroom_id=? AND user_id=?
    """, (classroom_id, user_id, classroom_id, user_id)).fetchone()
    
    if not access:
        return None
    
    return classroom

def get_classroom_students(classroom_id: int):
    """Get all students enrolled in a classroom"""
    db = get_db()
    rows = db.execute("""
        SELECT u.id, u.email, u.full_name, 
               CASE 
                 WHEN e.enrolled_at LIKE '%T%' THEN REPLACE(e.enrolled_at, 'T', ' ')
                 ELSE e.enrolled_at 
               END as enrolled_at
        FROM users u
        JOIN enrollments e ON e.user_id = u.id
        WHERE e.classroom_id = ? AND u.role = 'student'
        ORDER BY u.full_name, u.email
    """, (classroom_id,)).fetchall()
    return [dict(r) for r in rows]

def get_classroom_assignments(classroom_id: int):
    """Get all assignments for a classroom"""
    db = get_db()
    rows = db.execute("""
        SELECT id, title, due_at, created_at
        FROM assignments 
        WHERE classroom_id = ?
        ORDER BY created_at DESC
    """, (classroom_id,)).fetchall()
    return [dict(r) for r in rows]
