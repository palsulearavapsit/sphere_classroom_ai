"""
Advanced Analytics Service
Provides comprehensive data visualization and educational insights
"""
try:
    import pandas as pd
    import numpy as np
    import plotly.graph_objs as go
    import plotly.express as px
    from plotly.utils import PlotlyJSONEncoder
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False
    pd = None
    np = None
    go = None
    px = None
    PlotlyJSONEncoder = None

import json
from datetime import datetime, timedelta
from ..db import get_db

class AnalyticsService:
    
    def __init__(self):
        self.available = ANALYTICS_AVAILABLE
    
    def _get_db(self):
        """Get database connection safely"""
        try:
            return get_db()
        except RuntimeError:
            # Outside application context
            return None
    
    def get_student_performance_overview(self, student_id=None):
        """Get student performance analytics"""
        if not self.available:
            return {"error": "Analytics dependencies not available"}
        
        db = self._get_db()
        if not db:
            return {"error": "Database not available"}
        
        query = """
        SELECT 
            s.id,
            s.name as student_name,
            s.email,
            s.grade_level,
            AVG(sub.score) as avg_score,
            COUNT(sub.id) as total_submissions,
            MAX(sub.submitted_at) as last_activity
        FROM students s
        LEFT JOIN submissions sub ON s.id = sub.student_id
        """
        
        if student_id:
            query += " WHERE s.id = ?"
            params = (student_id,)
        else:
            query += " GROUP BY s.id ORDER BY avg_score DESC"
            params = ()
        
        try:
            if hasattr(self.db, 'execute'):
                # SQLite
                result = self.db.execute(query, params).fetchall()
                return [dict(row) for row in result]
            else:
                # MySQL
                cursor = self.db.cursor(dictionary=True)
                cursor.execute(query, params)
                result = cursor.fetchall()
                cursor.close()
                return result
        except Exception as e:
            print(f"Error in get_student_performance_overview: {e}")
            return []
    
    def get_assessment_analytics(self):
        """Get assessment performance analytics"""
        query = """
        SELECT 
            a.id,
            a.title,
            a.course_id,
            COUNT(s.id) as submission_count,
            AVG(s.score) as avg_score,
            MIN(s.score) as min_score,
            MAX(s.score) as max_score,
            STDDEV(s.score) as score_stddev
        FROM assessments a
        LEFT JOIN submissions s ON a.id = s.assessment_id
        GROUP BY a.id
        ORDER BY submission_count DESC
        """
        
        try:
            if hasattr(self.db, 'execute'):
                result = self.db.execute(query).fetchall()
                return [dict(row) for row in result]
            else:
                cursor = self.db.cursor(dictionary=True)
                cursor.execute(query)
                result = cursor.fetchall()
                cursor.close()
                return result
        except Exception as e:
            print(f"Error in get_assessment_analytics: {e}")
            return []
    
    def create_performance_chart(self, data_type="student_performance"):
        """Create interactive charts using Plotly"""
        
        if data_type == "student_performance":
            data = self.get_student_performance_overview()
            
            if not data:
                return self._create_empty_chart("No student performance data available")
            
            df = pd.DataFrame(data)
            
            # Create performance bar chart
            fig = px.bar(
                df, 
                x='student_name', 
                y='avg_score',
                title='Student Performance Overview',
                color='total_submissions',
                hover_data=['grade_level', 'last_activity']
            )
            
            fig.update_layout(
                xaxis_title="Students",
                yaxis_title="Average Score",
                showlegend=True
            )
            
        elif data_type == "assessment_analytics":
            data = self.get_assessment_analytics()
            
            if not data:
                return self._create_empty_chart("No assessment data available")
            
            df = pd.DataFrame(data)
            
            # Create assessment analytics chart
            fig = px.scatter(
                df, 
                x='submission_count', 
                y='avg_score',
                size='score_stddev',
                title='Assessment Analytics: Participation vs Performance',
                hover_data=['title']
            )
            
            fig.update_layout(
                xaxis_title="Number of Submissions",
                yaxis_title="Average Score"
            )
            
        elif data_type == "learning_progress":
            # Time-based learning progress
            data = self._get_learning_progress_data()
            
            if not data:
                return self._create_empty_chart("No progress data available")
            
            df = pd.DataFrame(data)
            
            fig = px.line(
                df, 
                x='date', 
                y='score',
                color='student_name',
                title='Learning Progress Over Time'
            )
            
        else:
            return self._create_empty_chart("Unknown chart type")
        
        # Convert to JSON for frontend
        graphJSON = json.dumps(fig, cls=PlotlyJSONEncoder)
        return graphJSON
    
    def _create_empty_chart(self, message):
        """Create empty chart with message"""
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(
            title="No Data Available",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False)
        )
        return json.dumps(fig, cls=PlotlyJSONEncoder)
    
    def _get_learning_progress_data(self):
        """Get learning progress data over time"""
        query = """
        SELECT 
            s.name as student_name,
            sub.score,
            DATE(sub.submitted_at) as date
        FROM students s
        JOIN submissions sub ON s.id = sub.student_id
        WHERE sub.submitted_at >= DATE('now', '-30 days')
        ORDER BY sub.submitted_at
        """
        
        try:
            if hasattr(self.db, 'execute'):
                result = self.db.execute(query).fetchall()
                return [dict(row) for row in result]
            else:
                cursor = self.db.cursor(dictionary=True)
                cursor.execute(query)
                result = cursor.fetchall()
                cursor.close()
                return result
        except Exception as e:
            print(f"Error in _get_learning_progress_data: {e}")
            return []
    
    def get_classroom_analytics(self, classroom_id=None):
        """Get classroom-specific analytics"""
        # This would require joining with enrollment data
        # For now, return sample data structure
        return {
            "total_students": 0,
            "avg_performance": 0,
            "active_assessments": 0,
            "completion_rate": 0
        }
    
    def generate_performance_report(self, student_id):
        """Generate comprehensive performance report for a student"""
        performance = self.get_student_performance_overview(student_id)
        
        if not performance:
            return {"error": "No data found for student"}
        
        student_data = performance[0]
        
        report = {
            "student_info": {
                "name": student_data.get('student_name', 'Unknown'),
                "email": student_data.get('email', 'Unknown'),
                "grade_level": student_data.get('grade_level', 'Unknown')
            },
            "performance_summary": {
                "average_score": round(student_data.get('avg_score', 0) or 0, 2),
                "total_submissions": student_data.get('total_submissions', 0) or 0,
                "last_activity": student_data.get('last_activity', 'Never')
            },
            "recommendations": self._generate_recommendations(student_data),
            "charts": {
                "progress_chart": self.create_performance_chart("learning_progress"),
                "performance_chart": self.create_performance_chart("student_performance")
            }
        }
        
        return report
    
    def _generate_recommendations(self, student_data):
        """Generate AI-powered recommendations based on performance"""
        avg_score = student_data.get('avg_score', 0) or 0
        total_submissions = student_data.get('total_submissions', 0) or 0
        
        recommendations = []
        
        if avg_score < 60:
            recommendations.append("Consider scheduling additional tutoring sessions")
            recommendations.append("Review fundamental concepts before attempting new material")
        elif avg_score < 80:
            recommendations.append("Good progress! Focus on challenging problem areas")
            recommendations.append("Practice more complex problems to improve further")
        else:
            recommendations.append("Excellent performance! Consider advanced materials")
            recommendations.append("Help other students to reinforce your knowledge")
        
        if total_submissions < 3:
            recommendations.append("Increase assignment completion rate")
            recommendations.append("Regular practice will improve performance")
        
        return recommendations
    
    def get_system_analytics(self):
        """Get system-wide analytics for admin dashboard"""
        try:
            stats = {}
            
            # User statistics
            if hasattr(self.db, 'execute'):
                stats['total_users'] = self.db.execute("SELECT COUNT(*) as count FROM users").fetchone()['count']
                stats['total_students'] = self.db.execute("SELECT COUNT(*) as count FROM users WHERE role='student'").fetchone()['count']
                stats['total_teachers'] = self.db.execute("SELECT COUNT(*) as count FROM users WHERE role='teacher'").fetchone()['count']
            
            # Activity statistics
            stats['total_submissions'] = 0  # Would query submissions table
            stats['total_assessments'] = 0  # Would query assessments table
            stats['total_ocr_extractions'] = 0  # Would query OCR table
            
            return stats
            
        except Exception as e:
            print(f"Error in get_system_analytics: {e}")
            return {
                "total_users": 0,
                "total_students": 0,
                "total_teachers": 0,
                "total_submissions": 0,
                "total_assessments": 0,
                "total_ocr_extractions": 0
            }

# Create global instance
analytics_service = AnalyticsService()