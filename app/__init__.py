import os
import json
from flask import Flask
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from .config import Config
from .db import init_db, get_db
from .auth import user_loader, auth_bp
from .routes.main import main_bp
from .routes.tutor import tutor_bp  # Re-enabled - should work with safe imports
from .routes.ocr import ocr_bp
from .routes.assessments import assess_bp  # Re-enabled - should work with safe imports
from .routes.classrooms import class_bp
from .routes.admin import admin_bp
from .routes.api import api_bp
from .routes.mysql import mysql_bp
# from .routes.analytics import analytics_bp  # Disabled - removed from navigation
from .routes.notifications import notifications_bp  # Re-enabled for live chat functionality
from .routes.grading import grading_bp  # Re-enabled after fixing Flask context issues
from .routes.content_generation import content_bp
from .routes.plagiarism import plagiarism_bp
from .routes.image_analysis import image_analysis_bp
# from .services.realtime_service import init_socketio  # Temporarily disabled
from .services.email_service import email_service

login_manager = LoginManager()
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(Config)

    # Security headers
    @app.after_request
    def add_headers(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["X-XSS-Protection"] = "1; mode=block"
        resp.headers["Referrer-Policy"] = "no-referrer-when-downgrade"
        return resp

    # DB
    init_db(app)

    # Auth
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    @login_manager.user_loader
    def _load(user_id):
        return user_loader(user_id)

    # CSRF
    csrf.init_app(app)

    # Rate limiting
    limiter = Limiter(get_remote_address, app=app, default_limits=["200 per hour"])

    # Template filters
    @app.template_filter('from_json')
    def from_json_filter(value):
        """Convert JSON string to Python object"""
        try:
            if isinstance(value, str):
                return json.loads(value)
            return value
        except (json.JSONDecodeError, TypeError):
            return {}

    # Email service
    email_service.init_app(app)

    # Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(tutor_bp, url_prefix="/tutor")  # Re-enabled
    
    # Data analysis routes
    try:
        from app.routes.data import data_bp
        app.register_blueprint(data_bp, url_prefix="/data")
        app.logger.info("Data routes registered successfully")
    except ImportError as e:
        app.logger.warning(f"Data routes not registered: {e}")
    
    # app.register_blueprint(data_bp, url_prefix="/data")  # Temporarily disabled due to numpy issues
    app.register_blueprint(ocr_bp, url_prefix="/ocr")
    app.register_blueprint(assess_bp, url_prefix="/assessments")  # Re-enabled
    app.register_blueprint(class_bp, url_prefix="/classrooms")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(mysql_bp, url_prefix="/mysql")
    # app.register_blueprint(analytics_bp, url_prefix="/analytics")  # Disabled - removed from navigation
    app.register_blueprint(notifications_bp, url_prefix="/notifications")  # Re-enabled for live chat functionality
    app.register_blueprint(grading_bp, url_prefix="/grading")  # Re-enabled after fixing Flask context issues
    app.register_blueprint(content_bp, url_prefix="/content")
    app.register_blueprint(plagiarism_bp, url_prefix="/plagiarism")
    app.register_blueprint(image_analysis_bp, url_prefix="/image-analysis")

    # Initialize WebSocket support
    # socketio = init_socketio(app)  # Temporarily disabled

    @app.route("/health")
    def health():
        try:
            conn = get_db()
            conn.execute("SELECT 1")
            status = "ok"
        except Exception as e:
            status = f"db_error: {e}"
        return {"status": status}

    # Handle disabled analytics routes
    @app.route("/analytics/")
    @app.route("/analytics/<path:path>")
    def disabled_analytics(path=None):
        from flask import flash, redirect, url_for
        flash("Analytics features have been disabled. Please use the main dashboard features.", "info")
        return redirect(url_for("main.home"))

    return app
