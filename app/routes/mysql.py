"""
MySQL Database Integration Routes
Provides admin interface for managing MySQL database connections and testing
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.services.mysql_data_service import mysql_data_service
import os

mysql_bp = Blueprint("mysql", __name__, url_prefix="/mysql")

@mysql_bp.route("/")
@login_required
def mysql_admin():
    """MySQL admin interface"""
    if not current_user.role == "admin":
        flash("Admin access required", "error")
        return redirect(url_for("main.dashboard"))
    
    # Check current configuration
    config_status = {
        'database_url': bool(os.getenv('DATABASE_URL')),
        'mysql_host': os.getenv('MYSQL_HOST', 'Not set'),
        'mysql_user': os.getenv('MYSQL_USER', 'Not set'),
        'mysql_database': os.getenv('MYSQL_DATABASE', 'Not set'),
        'connection_status': 'Unknown'
    }
    
    # Test connection
    try:
        conn = mysql_data_service.get_connection()
        if conn:
            config_status['connection_status'] = 'Connected'
            conn.close()
        else:
            config_status['connection_status'] = 'Failed - Check credentials'
    except Exception as e:
        config_status['connection_status'] = f'Error: {str(e)}'
    
    return render_template("admin_mysql.html", config=config_status)

@mysql_bp.route("/test", methods=["POST"])
@login_required
def test_connection():
    """Test MySQL connection"""
    if not current_user.role == "admin":
        return jsonify({"error": "Admin access required"}), 403
    
    try:
        conn = mysql_data_service.get_connection()
        if not conn:
            return jsonify({"error": "Failed to connect to MySQL. Check your configuration."}), 500
        
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]
        
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]
        
        cursor.close()
        
        return jsonify({
            "success": True,
            "version": version,
            "tables": tables[:10],  # Limit to first 10 tables
            "total_tables": len(tables)
        })
        
    except Exception as e:
        return jsonify({"error": f"Connection test failed: {str(e)}"}), 500

@mysql_bp.route("/schema", methods=["GET"])
@login_required
def get_schema():
    """Get database schema information"""
    if not current_user.role == "admin":
        return jsonify({"error": "Admin access required"}), 403
    
    try:
        schema_info = mysql_data_service.get_table_schema_info()
        return jsonify({"schema": schema_info})
    except Exception as e:
        return jsonify({"error": f"Failed to get schema: {str(e)}"}), 500

@mysql_bp.route("/query", methods=["POST"])
@login_required
def execute_query():
    """Execute a safe SELECT query"""
    if not current_user.role == "admin":
        return jsonify({"error": "Admin access required"}), 403
    
    query = request.json.get("query", "").strip()
    if not query:
        return jsonify({"error": "Query is required"}), 400
    
    try:
        result = mysql_data_service.execute_safe_query(query)
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": f"Query execution failed: {str(e)}"}), 500

@mysql_bp.route("/search_context", methods=["POST"])
@login_required
def search_context():
    """Test context search functionality"""
    if not current_user.role == "admin":
        return jsonify({"error": "Admin access required"}), 403
    
    search_term = request.json.get("search_term", "").strip()
    if not search_term:
        return jsonify({"error": "Search term is required"}), 400
    
    try:
        context = mysql_data_service.search_data_context(search_term, limit=10)
        return jsonify({"context": context})
    except Exception as e:
        return jsonify({"error": f"Context search failed: {str(e)}"}), 500