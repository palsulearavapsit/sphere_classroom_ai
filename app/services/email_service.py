"""
Email Service Module for Project Galileo
Handles all email notifications including assignments, grades, reminders, etc.
"""
import os
from flask import current_app, render_template_string
from flask_mail import Mail, Message
from datetime import datetime, timedelta
import threading

class EmailService:
    def __init__(self):
        self.mail = None
    
    def init_app(self, app):
        """Initialize Flask-Mail with the app"""
        self.mail = Mail(app)
    
    def send_async_email(self, msg):
        """Send email asynchronously"""
        try:
            with current_app.app_context():
                self.mail.send(msg)
                print(f"[SUCCESS] Email sent successfully to {msg.recipients}")
        except Exception as e:
            print(f"[ERROR] Failed to send email: {str(e)}")
    
    def send_email(self, subject, recipients, html_body, text_body=None):
        """Send email with both HTML and text versions"""
        if not isinstance(recipients, list):
            recipients = [recipients]
        
        try:
            msg = Message(
                subject=f"[SPHERE AI] {subject}",
                recipients=recipients,
                html=html_body,
                body=text_body or self._html_to_text(html_body)
            )
            
            # Send email in background thread
            thread = threading.Thread(target=self.send_async_email, args=[msg])
            thread.start()
            return True
            
        except Exception as e:
            print(f"[ERROR] Email preparation failed: {str(e)}")
            return False
    
    def _html_to_text(self, html_content):
        """Convert HTML to plain text for email clients that don't support HTML"""
        import re
        # Simple HTML to text conversion
        text = re.sub('<[^<]+?>', '', html_content)
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        return text.strip()
    
    # Assignment Notifications
    def notify_assignment_created(self, assignment, classroom, teacher, students):
        """Notify students when a new assignment is created"""
        subject = f"New Assignment: {assignment['title']}"
        
        for student in students:
            html_body = self._render_assignment_notification_template(
                student_name=student['name'],
                assignment_title=assignment['title'],
                classroom_name=classroom['name'],
                teacher_name=teacher['name'],
                due_date=assignment.get('due_date', 'No due date set'),
                assignment_id=assignment['id']
            )
            
            self.send_email(subject, [student['email']], html_body)
    
    def notify_assignment_graded(self, assignment, student, grade, feedback=None):
        """Notify student when assignment is graded"""
        subject = f"Assignment Graded: {assignment['title']}"
        
        html_body = self._render_grade_notification_template(
            student_name=student['name'],
            assignment_title=assignment['title'],
            grade=grade,
            feedback=feedback,
            assignment_id=assignment['id']
        )
        
        self.send_email(subject, [student['email']], html_body)
    
    def notify_assignment_deadline_reminder(self, assignment, classroom, students, days_before=1):
        """Send deadline reminders to students"""
        subject = f"Assignment Due Soon: {assignment['title']}"
        
        for student in students:
            html_body = self._render_deadline_reminder_template(
                student_name=student['name'],
                assignment_title=assignment['title'],
                classroom_name=classroom['name'],
                due_date=assignment.get('due_date', 'Soon'),
                days_before=days_before,
                assignment_id=assignment['id']
            )
            
            self.send_email(subject, [student['email']], html_body)
    
    # Classroom Notifications
    def notify_classroom_enrollment(self, classroom, student, teacher):
        """Notify when student joins a classroom"""
        # Notify student
        subject = f"Welcome to {classroom['name']}"
        html_body = self._render_enrollment_notification_template(
            student_name=student['name'],
            classroom_name=classroom['name'],
            teacher_name=teacher['name'],
            classroom_code=classroom['code']
        )
        self.send_email(subject, [student['email']], html_body)
        
        # Notify teacher
        subject = f"New Student Enrolled: {student['name']}"
        html_body = self._render_teacher_enrollment_notification_template(
            teacher_name=teacher['name'],
            student_name=student['name'],
            classroom_name=classroom['name']
        )
        self.send_email(subject, [teacher['email']], html_body)
    
    # User Management Notifications
    def notify_user_created(self, user, password=None):
        """Notify when new user account is created"""
        subject = "Welcome to Project Galileo"
        
        html_body = self._render_welcome_notification_template(
            user_name=user['name'],
            user_email=user['email'],
            user_role=user['role'],
            password=password
        )
        
        self.send_email(subject, [user['email']], html_body)
    
    def notify_password_reset(self, user, reset_token):
        """Notify user about password reset"""
        subject = "Password Reset Request"
        
        html_body = self._render_password_reset_template(
            user_name=user['name'],
            reset_token=reset_token
        )
        
        self.send_email(subject, [user['email']], html_body)
    
    # System Notifications
    def notify_system_maintenance(self, users, maintenance_time, duration):
        """Notify users about system maintenance"""
        subject = "Scheduled System Maintenance"
        
        for user in users:
            html_body = self._render_maintenance_notification_template(
                user_name=user['name'],
                maintenance_time=maintenance_time,
                duration=duration
            )
            
            self.send_email(subject, [user['email']], html_body)
    
    # Email Templates
    def _render_assignment_notification_template(self, student_name, assignment_title, classroom_name, teacher_name, due_date, assignment_id):
        """HTML template for new assignment notifications"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
                .highlight {{ background: #e3f2fd; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; margin: 15px 0; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎯 New Assignment Available</h1>
                </div>
                <div class="content">
                    <h2>Hello {student_name}!</h2>
                    <p>You have a new assignment in your <strong>{classroom_name}</strong> classroom.</p>
                    
                    <div class="highlight">
                        <h3>📝 Assignment Details:</h3>
                        <p><strong>Title:</strong> {assignment_title}</p>
                        <p><strong>Classroom:</strong> {classroom_name}</p>
                        <p><strong>Teacher:</strong> {teacher_name}</p>
                        <p><strong>Due Date:</strong> {due_date}</p>
                    </div>
                    
                    <p>Don't forget to complete your assignment on time!</p>
                    
                    <a href="http://localhost:5000/assessments/{assignment_id}" class="button">
                        View Assignment
                    </a>
                </div>
                <div class="footer">
                    <p>Project Galileo - Enhancing Education with AI</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _render_grade_notification_template(self, student_name, assignment_title, grade, feedback, assignment_id):
        """HTML template for grade notifications"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #4caf50 0%, #45a049 100%); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
                .grade-box {{ background: #e8f5e8; padding: 20px; border-radius: 5px; text-align: center; margin: 15px 0; }}
                .grade {{ font-size: 24px; font-weight: bold; color: #4caf50; }}
                .feedback {{ background: #fff3cd; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                .button {{ display: inline-block; background: #4caf50; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; margin: 15px 0; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Assignment Graded</h1>
                </div>
                <div class="content">
                    <h2>Hello {student_name}!</h2>
                    <p>Your assignment <strong>"{assignment_title}"</strong> has been graded.</p>
                    
                    <div class="grade-box">
                        <p>Your Grade:</p>
                        <div class="grade">{grade}</div>
                    </div>
                    
                    {f'<div class="feedback"><h3>📝 Teacher Feedback:</h3><p>{feedback}</p></div>' if feedback else ''}
                    
                    <a href="http://localhost:5000/assessments/{assignment_id}" class="button">
                        View Assignment
                    </a>
                </div>
                <div class="footer">
                    <p>Project Galileo - Enhancing Education with AI</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _render_deadline_reminder_template(self, student_name, assignment_title, classroom_name, due_date, days_before, assignment_id):
        """HTML template for deadline reminders"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
                .warning {{ background: #fff3cd; padding: 15px; border-radius: 5px; margin: 15px 0; border-left: 4px solid #ff9800; }}
                .button {{ display: inline-block; background: #ff9800; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; margin: 15px 0; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⏰ Assignment Due Soon</h1>
                </div>
                <div class="content">
                    <h2>Hello {student_name}!</h2>
                    
                    <div class="warning">
                        <h3>⚠️ Deadline Reminder</h3>
                        <p>Your assignment <strong>"{assignment_title}"</strong> in <strong>{classroom_name}</strong> is due in {days_before} day{'s' if days_before != 1 else ''}.</p>
                        <p><strong>Due Date:</strong> {due_date}</p>
                    </div>
                    
                    <p>Don't miss the deadline! Complete your assignment now.</p>
                    
                    <a href="http://localhost:5000/assessments/{assignment_id}" class="button">
                        Complete Assignment
                    </a>
                </div>
                <div class="footer">
                    <p>Project Galileo - Enhancing Education with AI</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _render_enrollment_notification_template(self, student_name, classroom_name, teacher_name, classroom_code):
        """HTML template for classroom enrollment notifications"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #2196f3 0%, #1976d2 100%); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
                .welcome-box {{ background: #e3f2fd; padding: 20px; border-radius: 5px; margin: 15px 0; }}
                .button {{ display: inline-block; background: #2196f3; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; margin: 15px 0; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎓 Welcome to Your Classroom</h1>
                </div>
                <div class="content">
                    <h2>Hello {student_name}!</h2>
                    <p>You have successfully enrolled in a new classroom.</p>
                    
                    <div class="welcome-box">
                        <h3>📚 Classroom Details:</h3>
                        <p><strong>Classroom:</strong> {classroom_name}</p>
                        <p><strong>Teacher:</strong> {teacher_name}</p>
                        <p><strong>Classroom Code:</strong> {classroom_code}</p>
                    </div>
                    
                    <p>Start exploring your new classroom and connect with your teacher and classmates!</p>
                    
                    <a href="http://localhost:5000/classrooms" class="button">
                        View Your Classrooms
                    </a>
                </div>
                <div class="footer">
                    <p>Project Galileo - Enhancing Education with AI</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _render_teacher_enrollment_notification_template(self, teacher_name, student_name, classroom_name):
        """HTML template for teacher enrollment notifications"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #9c27b0 0%, #7b1fa2 100%); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
                .student-info {{ background: #f3e5f5; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                .button {{ display: inline-block; background: #9c27b0; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; margin: 15px 0; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>👥 New Student Enrollment</h1>
                </div>
                <div class="content">
                    <h2>Hello {teacher_name}!</h2>
                    <p>A new student has joined your classroom.</p>
                    
                    <div class="student-info">
                        <h3>📊 Student Information:</h3>
                        <p><strong>Student Name:</strong> {student_name}</p>
                        <p><strong>Classroom:</strong> {classroom_name}</p>
                    </div>
                    
                    <p>Welcome your new student and help them get started!</p>
                    
                    <a href="http://localhost:5000/classrooms" class="button">
                        View Classroom
                    </a>
                </div>
                <div class="footer">
                    <p>Project Galileo - Enhancing Education with AI</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _render_welcome_notification_template(self, user_name, user_email, user_role, password):
        """HTML template for new user welcome notifications"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #4caf50 0%, #388e3c 100%); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
                .credentials {{ background: #e8f5e8; padding: 20px; border-radius: 5px; margin: 15px 0; }}
                .password {{ font-family: monospace; background: #fff; padding: 10px; border-radius: 3px; border: 1px solid #ddd; }}
                .button {{ display: inline-block; background: #4caf50; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; margin: 15px 0; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Welcome to SPHERE AI</h1>
                </div>
                <div class="content">
                    <h2>Hello {user_name}!</h2>
                    <p>Your account has been created on the Project Galileo. You're now part of our educational community!</p>
                    
                    <div class="credentials">
                        <h3>🔐 Your Account Details:</h3>
                        <p><strong>Email:</strong> {user_email}</p>
                        <p><strong>Role:</strong> {user_role.title()}</p>
                        {f'<p><strong>Temporary Password:</strong></p><div class="password">{password}</div><p><em>Please change this password after your first login.</em></p>' if password else '<p>Use your chosen password to log in.</p>'}
                    </div>
                    
                    <p>Get started by logging into your account and exploring the features!</p>
                    
                    <a href="http://localhost:5000/auth/login" class="button">
                        Login to SPHERE AI
                    </a>
                </div>
                <div class="footer">
                    <p>Project Galileo - Enhancing Education with AI</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _render_password_reset_template(self, user_name, reset_token):
        """HTML template for password reset notifications"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
                .security-notice {{ background: #ffebee; padding: 15px; border-radius: 5px; margin: 15px 0; border-left: 4px solid #f44336; }}
                .button {{ display: inline-block; background: #f44336; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; margin: 15px 0; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔒 Password Reset Request</h1>
                </div>
                <div class="content">
                    <h2>Hello {user_name}!</h2>
                    <p>You have requested to reset your password for your SPHERE AI account.</p>
                    
                    <div class="security-notice">
                        <h3>🛡️ Security Notice:</h3>
                        <p>If you did not request this password reset, please ignore this email. Your account remains secure.</p>
                    </div>
                    
                    <p>Click the button below to reset your password. This link will expire in 24 hours.</p>
                    
                    <a href="http://localhost:5000/auth/reset-password?token={reset_token}" class="button">
                        Reset Password
                    </a>
                    
                    <p><small>Or copy this link: http://localhost:5000/auth/reset-password?token={reset_token}</small></p>
                </div>
                <div class="footer">
                    <p>Project Galileo - Enhancing Education with AI</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _render_maintenance_notification_template(self, user_name, maintenance_time, duration):
        """HTML template for system maintenance notifications"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #607d8b 0%, #455a64 100%); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
                .maintenance-info {{ background: #e0f2f1; padding: 20px; border-radius: 5px; margin: 15px 0; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔧 Scheduled Maintenance</h1>
                </div>
                <div class="content">
                    <h2>Hello {user_name}!</h2>
                    <p>We wanted to inform you about scheduled maintenance on the Project Galileo.</p>
                    
                    <div class="maintenance-info">
                        <h3>🕐 Maintenance Details:</h3>
                        <p><strong>Start Time:</strong> {maintenance_time}</p>
                        <p><strong>Duration:</strong> {duration}</p>
                        <p><strong>Impact:</strong> The platform will be temporarily unavailable</p>
                    </div>
                    
                    <p>We apologize for any inconvenience and appreciate your patience as we work to improve our services.</p>
                </div>
                <div class="footer">
                    <p>Project Galileo - Enhancing Education with AI</p>
                </div>
            </div>
        </body>
        </html>
        """

# Global email service instance
email_service = EmailService()
