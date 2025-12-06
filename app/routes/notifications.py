"""
Real-time Notifications and Live Features Routes
"""
from flask import Blueprint, render_template, jsonify, request, current_app
from flask_login import login_required, current_user
from datetime import datetime
from ..services.realtime_service import get_user_notifications, send_notification, mark_notification_read
from ..db import get_db

notifications_bp = Blueprint("notifications", __name__, template_folder="../templates")

@notifications_bp.route("/", methods=["GET"])
@login_required
def notifications_home():
    """Notifications center"""
    notifications = get_user_notifications(current_user.id)
    return render_template("notifications.html", notifications=notifications)

@notifications_bp.route("/api/notifications", methods=["GET"])
@login_required
def get_notifications():
    """Get user notifications via API"""
    limit = request.args.get('limit', 20, type=int)
    notifications = get_user_notifications(current_user.id, limit)
    return jsonify(notifications)

@notifications_bp.route("/api/notifications/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_read(notification_id):
    """Mark notification as read"""
    mark_notification_read(current_user.id, notification_id)
    return jsonify({"success": True})

@notifications_bp.route("/live-chat")
@login_required
def live_chat():
    """Live chat interface"""
    return render_template("live_chat.html")

@notifications_bp.route("/api/classrooms")
@login_required
def get_classrooms():
    """Get available classrooms for current user"""
    try:
        conn = get_db()
        
        if current_user.role == 'admin':
            # Admin can see all classrooms
            classrooms = conn.execute("""
                SELECT id, name, join_code 
                FROM classrooms 
                ORDER BY name
            """).fetchall()
        elif current_user.role == 'teacher':
            # Teacher can see classrooms they created
            classrooms = conn.execute("""
                SELECT id, name, join_code 
                FROM classrooms 
                WHERE created_by = ?
                ORDER BY name
            """, (current_user.id,)).fetchall()
        else:
            # Student can see enrolled classrooms
            classrooms = conn.execute("""
                SELECT c.id, c.name, c.join_code 
                FROM classrooms c
                INNER JOIN enrollments e ON c.id = e.classroom_id
                WHERE e.user_id = ?
                ORDER BY c.name
            """, (current_user.id,)).fetchall()
        
        classroom_list = []
        for classroom in classrooms:
            classroom_list.append({
                'id': classroom['id'],
                'name': classroom['name'],
                'join_code': classroom['join_code'] or ''
            })
        
        # Add a general chat room for everyone
        classroom_list.insert(0, {
            'id': 'general',
            'name': 'General Chat',
            'join_code': ''
        })
        
        return jsonify({
            "success": True,
            "classrooms": classroom_list
        })
        
    except Exception as e:
        print(f"Error getting classrooms: {e}")
        return jsonify({"success": False, "error": "Failed to get classrooms"}), 500

@notifications_bp.route("/api/send-message", methods=["POST"])
@login_required
def send_chat_message():
    """Send a chat message (simple implementation without WebSocket)"""
    try:
        data = request.get_json() or {}
        message = data.get('message', '').strip()
        classroom_id = data.get('classroom_id')
        
        print(f"[DEBUG] Send message request: user={current_user.email}, classroom={classroom_id}, message='{message}'")
        
        if not message:
            return jsonify({"success": False, "error": "Message cannot be empty"}), 400
        
        conn = get_db()
        # Store message in database
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("""
            INSERT INTO chat_messages (user_id, classroom_id, message, created_at, user_email)
            VALUES (?, ?, ?, ?, ?)
        """, (
            current_user.id,
            classroom_id or 'general',
            message,
            timestamp,
            current_user.email
        ))
        conn.commit()
        
        print(f"[DEBUG] Message saved successfully")
        
        return jsonify({
            "success": True,
            "message": "Message sent",
            "user": current_user.email,
            "timestamp": timestamp
        })
        
    except Exception as e:
        print(f"[ERROR] Error sending message: {e}")
        return jsonify({"success": False, "error": "Failed to send message"}), 500

@notifications_bp.route("/api/get-messages")
@login_required  
def get_chat_messages():
    """Get recent chat messages"""
    try:
        classroom_id = request.args.get('classroom_id', 'general')
        limit = request.args.get('limit', 50, type=int)
        
        print(f"[DEBUG] Get messages request: user={current_user.email}, classroom={classroom_id}")
        
        conn = get_db()
        messages = conn.execute("""
            SELECT id, user_email, message, created_at
            FROM chat_messages 
            WHERE classroom_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (classroom_id, limit)).fetchall()
        
        # Reverse to get chronological order
        messages = list(reversed(messages))
        
        print(f"[DEBUG] Found {len(messages)} messages")
        
        return jsonify({
            "success": True,
            "messages": [
                {
                    "id": msg["id"],
                    "user_email": msg["user_email"],
                    "message": msg["message"],
                    "created_at": msg["created_at"]
                }
                for msg in messages
            ]
        })
        
    except Exception as e:
        print(f"[ERROR] Error getting messages: {e}")
        return jsonify({"success": False, "error": "Failed to get messages"}), 500

@notifications_bp.route("/api/send-test-notification", methods=["POST"])
@login_required
def send_test_notification():
    """Send test notification (for demonstration)"""
    data = request.get_json() or {}
    title = data.get('title', 'Test Notification')
    message = data.get('message', 'This is a test notification')
    
    send_notification(current_user.id, title, message, 'info')
    return jsonify({"success": True, "message": "Test notification sent"})

@notifications_bp.route("/preferences", methods=["GET"])
@login_required
def notification_preferences():
    """Display user notification preferences"""
    conn = get_db()
    
    # Get or create user preferences
    prefs = conn.execute("""
        SELECT * FROM notification_preferences WHERE user_id = ?
    """, (current_user.id,)).fetchone()
    
    if not prefs:
        # Create default preferences
        conn.execute("""
            INSERT INTO notification_preferences 
            (user_id, email_assignments, email_grades, email_enrollments, email_reminders, email_announcements)
            VALUES (?, 1, 1, 1, 1, 1)
        """, (current_user.id,))
        conn.commit()
        
        prefs = conn.execute("""
            SELECT * FROM notification_preferences WHERE user_id = ?
        """, (current_user.id,)).fetchone()
    
    return render_template("notification_preferences.html", preferences=dict(prefs))

@notifications_bp.route("/preferences", methods=["POST"])
@login_required
def update_notification_preferences():
    """Update user notification preferences"""
    data = request.get_json() or {}
    
    try:
        conn = get_db()
        conn.execute("""
            UPDATE notification_preferences 
            SET email_assignments = ?,
                email_grades = ?,
                email_enrollments = ?,
                email_reminders = ?,
                email_announcements = ?
            WHERE user_id = ?
        """, (
            1 if data.get('email_assignments') else 0,
            1 if data.get('email_grades') else 0,
            1 if data.get('email_enrollments') else 0,
            1 if data.get('email_reminders') else 0,
            1 if data.get('email_announcements') else 0,
            current_user.id
        ))
        conn.commit()
        
        return jsonify({"success": True, "message": "Preferences updated successfully"})
        
    except Exception as e:
        current_app.logger.error(f"Failed to update notification preferences: {e}")
        return jsonify({"success": False, "message": "Failed to update preferences"}), 500

def user_wants_notification(user_id, notification_type):
    """Check if user wants a specific type of notification"""
    try:
        conn = get_db()
        result = conn.execute(f"""
            SELECT {notification_type} FROM notification_preferences WHERE user_id = ?
        """, (user_id,)).fetchone()
        
        return result and result[0] == 1
    except:
        return True  # Default to sending notifications if preference not found