-- Minimal MySQL schema to replace JSON stores when FORCE_DB is enabled.
-- Users
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('student','teacher','admin')),
  full_name TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Classrooms
CREATE TABLE IF NOT EXISTS classrooms (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  join_code TEXT NOT NULL UNIQUE,
  created_by INTEGER NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
);

-- Enrollments
CREATE TABLE IF NOT EXISTS enrollments (
  user_id INTEGER NOT NULL,
  classroom_id INTEGER NOT NULL,
  enrolled_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id, classroom_id),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (classroom_id) REFERENCES classrooms(id) ON DELETE CASCADE
);

-- Assignments / Tests
CREATE TABLE IF NOT EXISTS assignments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  classroom_id INTEGER,
  title TEXT NOT NULL,
  content_json TEXT NOT NULL,            -- JSON string: {questions:[{q,options,answer}], ...}
  time_limit_minutes INTEGER DEFAULT 0,
  due_at TIMESTAMP NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (classroom_id) REFERENCES classrooms(id) ON DELETE SET NULL
);

-- Submissions
CREATE TABLE IF NOT EXISTS submissions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  assignment_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  answers_json TEXT NOT NULL,
  score REAL NOT NULL DEFAULT 0,
  ai_graded INTEGER DEFAULT 0,
  ai_feedback TEXT,
  manual_feedback TEXT,
  plagiarism_score REAL DEFAULT 0.0,
  plagiarism_checked INTEGER DEFAULT 0,
  submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  graded_at TIMESTAMP,
  FOREIGN KEY (assignment_id) REFERENCES assignments(id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Tutor Sessions (chat history)
CREATE TABLE IF NOT EXISTS tutor_sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  title TEXT NOT NULL DEFAULT 'Session',
  messages_json TEXT NOT NULL DEFAULT '[]',  -- running transcript
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- RAG Documents
CREATE TABLE IF NOT EXISTS documents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  path TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  namespace TEXT NOT NULL DEFAULT 'default',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- RAG Chunks (embedding as BLOB for FAISS rebuild; fallback LIKE on text)
CREATE TABLE IF NOT EXISTS chunks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  document_id INTEGER NOT NULL,
  chunk_index INTEGER NOT NULL,
  text TEXT NOT NULL,
  embedding BLOB NULL,
  FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

-- OCR Extractions
CREATE TABLE IF NOT EXISTS ocr_extractions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  image_path TEXT NOT NULL,
  text TEXT NOT NULL,
  struct_json TEXT NOT NULL DEFAULT '{}',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Notification Preferences
CREATE TABLE IF NOT EXISTS notification_preferences (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL UNIQUE,
  email_assignments INTEGER DEFAULT 1,
  email_grades INTEGER DEFAULT 1,
  email_enrollments INTEGER DEFAULT 1,
  email_reminders INTEGER DEFAULT 1,
  email_announcements INTEGER DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Assessments (alias for assignments for AI features)
CREATE TABLE IF NOT EXISTS assessments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  classroom_id INTEGER,
  title TEXT NOT NULL,
  content_json TEXT NOT NULL,            -- JSON string: {questions:[{q,options,answer}], ...}
  time_limit_minutes INTEGER DEFAULT 0,
  due_at TIMESTAMP NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (classroom_id) REFERENCES classrooms(id) ON DELETE SET NULL
);

-- Plagiarism Checks
CREATE TABLE IF NOT EXISTS plagiarism_checks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER,
  assignment_id INTEGER,
  text_hash TEXT NOT NULL,
  content_sample TEXT,
  plagiarism_score REAL NOT NULL DEFAULT 0.0,
  analysis_data TEXT,  -- JSON string with detailed analysis results
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
  FOREIGN KEY (assignment_id) REFERENCES assignments(id) ON DELETE SET NULL
);

-- Image Analyses
CREATE TABLE IF NOT EXISTS image_analyses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  image_hash TEXT NOT NULL,
  analysis_type TEXT NOT NULL,
  analysis_result TEXT NOT NULL,  -- JSON string with analysis results
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Chat Messages
CREATE TABLE IF NOT EXISTS chat_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  classroom_id TEXT NOT NULL DEFAULT 'general',
  message TEXT NOT NULL,
  user_email TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Seed admin/teacher/student if not present (idempotent)
-- Password for all demo users: password123
-- Hash generated with: pbkdf2_sha256.hash("password123")
INSERT OR IGNORE INTO users (id,email,password_hash,role,full_name)
VALUES
  (1,'student@ai.com','$pbkdf2-sha256$29000$cw5BiNG6F.K8F2JMyTlHKA$rPA.O/fQnSQsIicYj/o5QGwokZkGZ4B31QMwNYZxAsQ', 'student','Student One'),
  (2,'teacher@ai.com','$pbkdf2-sha256$29000$cw5BiNG6F.K8F2JMyTlHKA$rPA.O/fQnSQsIicYj/o5QGwokZkGZ4B31QMwNYZxAsQ', 'teacher','Teacher One'),
  (3,'admin@ai.com','$pbkdf2-sha256$29000$cw5BiNG6F.K8F2JMyTlHKA$rPA.O/fQnSQsIicYj/o5QGwokZkGZ4B31QMwNYZxAsQ', 'admin','Admin User');

-- Default notification preferences for demo users
INSERT OR IGNORE INTO notification_preferences (user_id, email_assignments, email_grades, email_enrollments, email_reminders, email_announcements)
VALUES
  (1, 1, 1, 1, 1, 1),
  (2, 1, 1, 1, 1, 1),
  (3, 1, 1, 1, 1, 1);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_assignments_classroom ON assignments(classroom_id);
CREATE INDEX IF NOT EXISTS idx_submissions_assignment ON submissions(assignment_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_user ON enrollments(user_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_class ON enrollments(classroom_id);
CREATE INDEX IF NOT EXISTS idx_notification_prefs_user ON notification_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_plagiarism_checks_user ON plagiarism_checks(user_id);
CREATE INDEX IF NOT EXISTS idx_plagiarism_checks_assignment ON plagiarism_checks(assignment_id);
CREATE INDEX IF NOT EXISTS idx_image_analyses_hash ON image_analyses(image_hash);
CREATE INDEX IF NOT EXISTS idx_image_analyses_type ON image_analyses(analysis_type);
CREATE INDEX IF NOT EXISTS idx_chat_messages_classroom ON chat_messages(classroom_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_user ON chat_messages(user_id);
