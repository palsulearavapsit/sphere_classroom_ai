"""
MySQL Data Service for AI Chatbot
Provides access to MySQL database data for contextual AI responses
"""

import json
import os
import mysql.connector
from urllib.parse import urlparse
from flask import current_app


class MySQLDataService:
    """Service to query MySQL database for chatbot context"""
    
    def __init__(self):
        self.conn = None
    
    def get_connection(self):
        """Get MySQL connection"""
        if not self.conn:
            self.conn = self._create_mysql_connection()
        return self.conn
    
    def _create_mysql_connection(self):
        """Create a MySQL connection for data queries"""
        try:
            # Try DATABASE_URL first (for existing setups)
            database_url = current_app.config.get("DATABASE_URL")
            if database_url:
                parsed = urlparse(database_url)
                config = {
                    'host': parsed.hostname,
                    'port': parsed.port or 3306,
                    'user': parsed.username,
                    'password': parsed.password,
                    'database': parsed.path.lstrip('/'),
                    'autocommit': True,
                }
            else:
                # Use individual environment variables
                config = {
                    'host': os.getenv('MYSQL_HOST', 'localhost'),
                    'port': int(os.getenv('MYSQL_PORT', 3306)),
                    'user': os.getenv('MYSQL_USER'),
                    'password': os.getenv('MYSQL_PASSWORD'),
                    'database': os.getenv('MYSQL_DATABASE'),
                    'autocommit': True,
                }
                
                # Check if all required fields are present
                if not all([config['user'], config['password'], config['database']]):
                    current_app.logger.info("MySQL credentials not configured - database context disabled")
                    return None
            
            return mysql.connector.connect(**config)
        except Exception as e:
            current_app.logger.error(f"Failed to connect to MySQL: {e}")
            return None
    
    def search_data_context(self, query_text, limit=10):
        """
        Search database for relevant context based on user query
        Returns formatted data that can be used by the AI chatbot
        """
        try:
            conn = self.get_connection()
            if not conn:
                return "No database connection available."
            
            cursor = conn.cursor(dictionary=True)
            context_data = []
            
            # Search in multiple relevant tables
            table_searches = [
                self._search_students(cursor, query_text, limit),
                self._search_courses(cursor, query_text, limit),
                self._search_assessments(cursor, query_text, limit),
                self._search_submissions(cursor, query_text, limit),
                self._search_analytics(cursor, query_text, limit)
            ]
            
            for search_result in table_searches:
                if search_result:
                    context_data.extend(search_result)
            
            cursor.close()
            
            if not context_data:
                return "No relevant data found in database."
            
            return self._format_context_data(context_data)
            
        except Exception as e:
            current_app.logger.error(f"MySQL search error: {e}")
            return f"Database query error: {str(e)}"
    
    def _search_students(self, cursor, query_text, limit):
        """Search student-related data"""
        try:
            # Adjust table and column names based on your actual schema
            sql = """
            SELECT 'student' as data_type, id, name, email, grade_level, enrollment_date
            FROM students 
            WHERE name LIKE %s OR email LIKE %s OR grade_level LIKE %s
            LIMIT %s
            """
            search_term = f"%{query_text}%"
            cursor.execute(sql, (search_term, search_term, search_term, limit))
            return cursor.fetchall()
        except Exception as e:
            current_app.logger.warning(f"Student search failed: {e}")
            return []
    
    def _search_courses(self, cursor, query_text, limit):
        """Search course-related data"""
        try:
            sql = """
            SELECT 'course' as data_type, id, course_name, course_code, description, instructor
            FROM courses 
            WHERE course_name LIKE %s OR course_code LIKE %s OR description LIKE %s OR instructor LIKE %s
            LIMIT %s
            """
            search_term = f"%{query_text}%"
            cursor.execute(sql, (search_term, search_term, search_term, search_term, limit))
            return cursor.fetchall()
        except Exception as e:
            current_app.logger.warning(f"Course search failed: {e}")
            return []
    
    def _search_assessments(self, cursor, query_text, limit):
        """Search assessment-related data"""
        try:
            sql = """
            SELECT 'assessment' as data_type, id, title, description, course_id, due_date, total_points
            FROM assessments 
            WHERE title LIKE %s OR description LIKE %s
            LIMIT %s
            """
            search_term = f"%{query_text}%"
            cursor.execute(sql, (search_term, search_term, limit))
            return cursor.fetchall()
        except Exception as e:
            current_app.logger.warning(f"Assessment search failed: {e}")
            return []
    
    def _search_submissions(self, cursor, query_text, limit):
        """Search submission-related data"""
        try:
            sql = """
            SELECT 'submission' as data_type, s.id, s.student_id, s.assessment_id, s.score, s.submitted_at,
                   st.name as student_name, a.title as assessment_title
            FROM submissions s
            JOIN students st ON s.student_id = st.id
            JOIN assessments a ON s.assessment_id = a.id
            WHERE st.name LIKE %s OR a.title LIKE %s
            LIMIT %s
            """
            search_term = f"%{query_text}%"
            cursor.execute(sql, (search_term, search_term, limit))
            return cursor.fetchall()
        except Exception as e:
            current_app.logger.warning(f"Submission search failed: {e}")
            return []
    
    def _search_analytics(self, cursor, query_text, limit):
        """Search analytics/performance data"""
        try:
            sql = """
            SELECT 'analytics' as data_type, student_id, course_id, avg_score, completion_rate, last_activity
            FROM student_analytics 
            WHERE student_id IN (
                SELECT id FROM students WHERE name LIKE %s
            ) OR course_id IN (
                SELECT id FROM courses WHERE course_name LIKE %s
            )
            LIMIT %s
            """
            search_term = f"%{query_text}%"
            cursor.execute(sql, (search_term, search_term, limit))
            return cursor.fetchall()
        except Exception as e:
            current_app.logger.warning(f"Analytics search failed: {e}")
            return []
    
    def _format_context_data(self, data):
        """Format database results for AI context"""
        if not data:
            return "No data found."
        
        formatted_sections = []
        
        # Group by data type
        data_by_type = {}
        for item in data:
            data_type = item.get('data_type', 'unknown')
            if data_type not in data_by_type:
                data_by_type[data_type] = []
            data_by_type[data_type].append(item)
        
        # Format each section
        for data_type, items in data_by_type.items():
            section = f"\n=== {data_type.upper()} DATA ===\n"
            
            for item in items[:5]:  # Limit items per type
                item_str = []
                for key, value in item.items():
                    if key != 'data_type' and value is not None:
                        item_str.append(f"{key}: {value}")
                section += "- " + ", ".join(item_str) + "\n"
            
            formatted_sections.append(section)
        
        return "\n".join(formatted_sections)
    
    def get_table_schema_info(self):
        """Get information about available tables for the AI"""
        try:
            conn = self.get_connection()
            if not conn:
                return "No database connection available."
            
            cursor = conn.cursor()
            cursor.execute("SHOW TABLES")
            tables = [table[0] for table in cursor.fetchall()]
            
            schema_info = "Available database tables:\n"
            for table in tables[:10]:  # Limit to first 10 tables
                try:
                    cursor.execute(f"DESCRIBE {table}")
                    columns = cursor.fetchall()
                    schema_info += f"\n{table}: {', '.join([col[0] for col in columns[:5]])}"
                except:
                    schema_info += f"\n{table}: (structure not accessible)"
            
            cursor.close()
            return schema_info
            
        except Exception as e:
            current_app.logger.error(f"Schema info error: {e}")
            return f"Cannot retrieve schema information: {str(e)}"
    
    def execute_safe_query(self, sql_query, params=None):
        """Execute a safe SELECT query"""
        try:
            # Only allow SELECT queries for safety
            if not sql_query.strip().upper().startswith('SELECT'):
                return "Only SELECT queries are allowed for safety."
            
            conn = self.get_connection()
            if not conn:
                return "No database connection available."
            
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql_query, params or ())
            results = cursor.fetchall()
            cursor.close()
            
            if not results:
                return "Query returned no results."
            
            # Format results
            formatted_results = "Query Results:\n"
            for i, row in enumerate(results[:20]):  # Limit to 20 rows
                formatted_results += f"Row {i+1}: {dict(row)}\n"
            
            if len(results) > 20:
                formatted_results += f"... and {len(results) - 20} more rows"
            
            return formatted_results
            
        except Exception as e:
            current_app.logger.error(f"Safe query error: {e}")
            return f"Query execution error: {str(e)}"


# Global instance
mysql_data_service = MySQLDataService()