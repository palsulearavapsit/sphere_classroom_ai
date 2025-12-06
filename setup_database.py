#!/usr/bin/env python3
"""
MySQL Database Setup Script for Project Galileo
This script creates the database and populates it with sample data
"""

import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

def setup_mysql_database():
    """Set up MySQL database with sample data"""
    
    # Load environment variables
    load_dotenv()
    
    mysql_config = {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'port': int(os.getenv('MYSQL_PORT', 3306)),
        'user': os.getenv('MYSQL_USER', 'root'),
        'password': os.getenv('MYSQL_PASSWORD', ''),
    }
    
    database_name = os.getenv('MYSQL_DATABASE', 'sphere_ai_platform')
    
    try:
        # Connect to MySQL server (without specifying database)
        print("Connecting to MySQL server...")
        connection = mysql.connector.connect(**mysql_config)
        cursor = connection.cursor()
        
        # Create database
        print(f"Creating database '{database_name}'...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database_name}")
        cursor.execute(f"USE {database_name}")
        
        # Read and execute the SQL setup file
        with open('setup_mysql_database.sql', 'r') as sql_file:
            sql_content = sql_file.read()
        
        # Remove CREATE DATABASE and USE statements since we already handled them
        sql_lines = sql_content.split('\n')
        filtered_lines = []
        for line in sql_lines:
            line = line.strip()
            if not line.startswith('CREATE DATABASE') and not line.startswith('USE ') and line:
                filtered_lines.append(line)
        
        sql_content = '\n'.join(filtered_lines)
        
        # Split and execute SQL statements properly
        sql_statements = []
        current_statement = ""
        
        for line in sql_content.split('\n'):
            line = line.strip()
            if line and not line.startswith('--'):
                current_statement += line + " "
                if line.endswith(';'):
                    sql_statements.append(current_statement.strip()[:-1])  # Remove the semicolon
                    current_statement = ""
        
        print(f"Executing {len(sql_statements)} SQL statements...")
        for i, statement in enumerate(sql_statements):
            if statement.strip():
                try:
                    print(f"  • Statement {i+1}: {statement[:60]}{'...' if len(statement) > 60 else ''}")
                    cursor.execute(statement)
                    connection.commit()
                except Error as e:
                    print(f"    ⚠️  Warning: {e}")
                    connection.rollback()
        print(f"\n✅ Database '{database_name}' setup completed successfully!")
        
        # Display table counts
        print("\n📊 Database Contents:")
        tables = ['students', 'courses', 'assessments', 'submissions', 'student_analytics']
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  • {table}: {count} records")
            except:
                print(f"  • {table}: table not found")
        
        print(f"\n🔗 Connection Details:")
        print(f"  • Host: {mysql_config['host']}")
        print(f"  • Port: {mysql_config['port']}")
        print(f"  • Database: {database_name}")
        print(f"  • User: {mysql_config['user']}")
        
    except Error as e:
        print(f"❌ Error setting up MySQL database: {e}")
        return False
    
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            print("\n📡 MySQL connection closed.")
    
    return True

def test_connection():
    """Test the MySQL connection with the configured settings"""
    load_dotenv()
    
    mysql_config = {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'port': int(os.getenv('MYSQL_PORT', 3306)),
        'user': os.getenv('MYSQL_USER', 'root'),
        'password': os.getenv('MYSQL_PASSWORD', ''),
        'database': os.getenv('MYSQL_DATABASE', 'sphere_ai_platform')
    }
    
    try:
        print("Testing MySQL connection...")
        connection = mysql.connector.connect(**mysql_config)
        cursor = connection.cursor()
        
        # Test basic query
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]
        print(f"✅ Connected successfully! MySQL version: {version}")
        
        # Test sample query
        cursor.execute("SELECT COUNT(*) FROM students")
        student_count = cursor.fetchone()[0]
        print(f"✅ Sample query successful! Found {student_count} students in database.")
        
        return True
        
    except Error as e:
        print(f"❌ Connection test failed: {e}")
        return False
    
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    print("🚀 Setting up MySQL Database for Project Galileo")
    print("=" * 60)
    
    # Setup database
    if setup_mysql_database():
        print("\n" + "=" * 60)
        # Test connection
        test_connection()
        
        print("\n🎉 Setup completed! You can now:")
        print("  1. Restart your Flask application")
        print("  2. Go to http://localhost:5000/mysql/ to test the connection")
        print("  3. Chat with the AI tutor - it now has access to your MySQL data!")
    else:
        print("\n❌ Setup failed. Please check your MySQL configuration.")