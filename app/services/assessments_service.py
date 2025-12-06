import json, random, os, uuid
from werkzeug.utils import secure_filename
from ..db import get_db
from ..ai.gemini_client import ask_gemini

def list_tests(user_id:int):
    db = get_db()
    rows = db.execute("SELECT id, title, due_at FROM assignments ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]

def fetch_test(test_id:int):
    db = get_db()
    row = db.execute("SELECT id,title,content_json,time_limit_minutes FROM assignments WHERE id=?", (test_id,)).fetchone()
    if not row: return None
    data = dict(row)
    data["content"] = json.loads(row["content_json"])
    return data

def submit_answers(user_id:int, test_id:int, answers:list):
    # naive scoring: 1 point per correct
    test = fetch_test(test_id)
    if not test: return {"error":"test not found"}
    content = test["content"]
    correct = 0
    for i,q in enumerate(content.get("questions",[])):
        if i < len(answers) and str(answers[i]).strip().lower() == str(q.get("answer","")).strip().lower():
            correct += 1
    score = correct / max(1, len(content.get("questions",[]))) * 100
    db = get_db()
    db.execute("INSERT INTO submissions(assignment_id,user_id,answers_json,score) VALUES(?,?,?,?)",
               (test_id, user_id, json.dumps(answers), float(score)))
    db.commit()
    return {"score": score}

def upload_pdf_assessment(file, title, description, teacher_id, classroom_id):
    """Upload and save PDF assessment"""
    # Generate unique filename
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4()}_{filename}"
    
    # Create uploads directory if it doesn't exist
    upload_dir = os.path.join(os.getcwd(), 'uploads', 'assessments')
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save file
    file_path = os.path.join(upload_dir, unique_filename)
    file.save(file_path)
    
    # Create assessment record in database
    db = get_db()
    
    # Create content JSON with PDF info
    content = {
        "type": "pdf",
        "filename": unique_filename,
        "original_filename": filename,
        "file_path": file_path,
        "description": description
    }
    
    db.execute("""
        INSERT INTO assignments(classroom_id, title, content_json, time_limit_minutes, due_at) 
        VALUES(?, ?, ?, ?, datetime('now', '+7 days'))
    """, (classroom_id, title, json.dumps(content), 60))
    
    db.commit()
    
    # Get the inserted ID
    row = db.execute("SELECT last_insert_rowid() as id").fetchone()
    
    return {"id": row["id"], "title": title, "filename": unique_filename}

def generate_adaptive_test(topic:str, level:str="medium"):
    prompt = f"Create a {level} difficulty 5-question multiple-choice test on {topic} with JSON output {{questions:[{{q,options,answer}}]}}."
    txt = ask_gemini(prompt)
    # naive JSON recovery
    import json
    try:
        data = json.loads(txt)
    except Exception:
        # fallback generate simple items
        data = {"questions":[
            {"q":f"Sample on {topic} #{i+1}","options":["A","B","C","D"],"answer":"A"} for i in range(5)
        ]}
    return data
