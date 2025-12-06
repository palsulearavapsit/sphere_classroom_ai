"""
Real-time Features Service
WebSocket-based real-time notifications, live chat, and collaboration
"""
from flask import Flask
# Lazy import for SocketIO to avoid issues during debug mode
try:
    from flask_socketio import SocketIO, emit, join_room, leave_room
    SOCKETIO_AVAILABLE = True
except ImportError:
    SocketIO = None
    emit = None
    join_room = None
    leave_room = None
    SOCKETIO_AVAILABLE = False
    print("SocketIO not available - notifications will work in basic mode")

from flask_login import current_user
import json
from datetime import datetime
from ..db import get_db

# Global SocketIO instance
socketio = None

def init_socketio(app):
    """Initialize SocketIO with the Flask app"""
    global socketio
    
    if not SOCKETIO_AVAILABLE:
        print("SocketIO not available - real-time features disabled")
        return None
        
    socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)
    
    # Real-time event handlers
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        if current_user.is_authenticated:
            print(f"User {current_user.email} connected")
            emit('status', {'msg': f'Welcome {current_user.email}!'})
        else:
            print("Anonymous user connected")
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        if current_user.is_authenticated:
            print(f"User {current_user.email} disconnected")
    
    # Additional event handlers can be added here
    return socketio
    def handle_classroom_message(data):
        """Handle real-time classroom chat"""
        if current_user.is_authenticated:
            classroom_id = data.get('classroom_id')
            message = data.get('message', '').strip()
            
            if message:
                message_data = {
                    'user': current_user.email,
                    'user_role': current_user.role,
                    'message': message,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Broadcast to all users in the classroom
                emit('new_message', message_data, room=f"classroom_{classroom_id}")
                
                # Store message in database (optional)
                store_classroom_message(classroom_id, current_user.id, message)
    
    @socketio.on('typing_indicator')
    def handle_typing(data):
        """Handle typing indicators"""
        if current_user.is_authenticated:
            classroom_id = data.get('classroom_id')
            is_typing = data.get('is_typing', False)
            
            emit('user_typing', {
                'user': current_user.email,
                'is_typing': is_typing,
                'timestamp': datetime.now().isoformat()
            }, room=f"classroom_{classroom_id}", include_self=False)
    
    @socketio.on('assessment_progress')
    def handle_assessment_progress(data):
        """Handle real-time assessment progress updates"""
        if current_user.is_authenticated and current_user.role in ['teacher', 'admin']:
            assessment_id = data.get('assessment_id')
            progress_data = data.get('progress', {})
            
            # Broadcast progress update to teachers monitoring the assessment
            emit('progress_update', {
                'assessment_id': assessment_id,
                'progress': progress_data,
                'timestamp': datetime.now().isoformat()
            }, room=f"assessment_{assessment_id}")
    
    @socketio.on('notification_read')
    def handle_notification_read(data):
        """Mark notification as read"""
        if current_user.is_authenticated:
            notification_id = data.get('notification_id')
            mark_notification_read(current_user.id, notification_id)
            emit('notification_updated', {'notification_id': notification_id, 'status': 'read'})
    
    return socketio

def store_classroom_message(classroom_id, user_id, message):
    """Store classroom message in database"""
    try:
        db = get_db()
        if hasattr(db, 'execute'):
            # SQLite
            db.execute("""
                INSERT INTO classroom_messages (classroom_id, user_id, message, created_at)
                VALUES (?, ?, ?, datetime('now'))
            """, (classroom_id, user_id, message))
            db.commit()
        else:
            # MySQL - would need to create the table first
            pass
    except Exception as e:
        print(f"Error storing classroom message: {e}")

def mark_notification_read(user_id, notification_id):
    """Mark a notification as read"""
    try:
        db = get_db()
        if hasattr(db, 'execute'):
            db.execute("""
                UPDATE notifications SET is_read = 1, read_at = datetime('now')
                WHERE id = ? AND user_id = ?
            """, (notification_id, user_id))
            db.commit()
    except Exception as e:
        print(f"Error marking notification as read: {e}")

def send_notification(user_id, title, message, notification_type='info'):
    """Send real-time notification to user"""
    global socketio
    
    if socketio:
        notification_data = {
            'title': title,
            'message': message,
            'type': notification_type,
            'timestamp': datetime.now().isoformat()
        }
        
        # Store in database
        try:
            db = get_db()
            if hasattr(db, 'execute'):
                db.execute("""
                    INSERT INTO notifications (user_id, title, message, type, created_at)
                    VALUES (?, ?, ?, ?, datetime('now'))
                """, (user_id, title, message, notification_type))
                db.commit()
        except Exception as e:
            print(f"Error storing notification: {e}")
        
        # Send real-time notification
        socketio.emit('new_notification', notification_data, room=f"user_{user_id}")

def broadcast_classroom_update(classroom_id, update_type, data):
    """Broadcast update to all users in a classroom"""
    global socketio
    
    if socketio:
        socketio.emit('classroom_update', {
            'type': update_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }, room=f"classroom_{classroom_id}")

def broadcast_assessment_update(assessment_id, update_type, data):
    """Broadcast assessment update to relevant users"""
    global socketio
    
    if socketio:
        socketio.emit('assessment_update', {
            'type': update_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }, room=f"assessment_{assessment_id}")

def notify_assignment_due(user_id, assignment_title, due_date):
    """Send notification about upcoming assignment due date"""
    send_notification(
        user_id=user_id,
        title="Assignment Due Soon",
        message=f"{assignment_title} is due on {due_date}",
        notification_type="warning"
    )

def notify_grade_posted(user_id, assignment_title, grade):
    """Send notification about posted grade"""
    send_notification(
        user_id=user_id,
        title="Grade Posted",
        message=f"Your grade for {assignment_title} is {grade}",
        notification_type="success"
    )

def get_user_notifications(user_id, limit=20):
    """Get user's recent notifications"""
    try:
        db = get_db()
        if hasattr(db, 'execute'):
            notifications = db.execute("""
                SELECT id, title, message, type, is_read, created_at
                FROM notifications
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit)).fetchall()
            return [dict(n) for n in notifications]
    except Exception as e:
        print(f"Error getting notifications: {e}")
    
    return []