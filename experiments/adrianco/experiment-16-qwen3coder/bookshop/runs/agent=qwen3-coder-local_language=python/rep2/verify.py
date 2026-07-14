#!/usr/bin/env python3
"""
Simple verification that the application can be imported and has the required structure.
"""
import os
import sys

def test_imports():
    """Test that all required modules can be imported"""
    try:
        from flask import Flask
        from flask_sqlalchemy import SQLAlchemy
        print("✓ Flask and SQLAlchemy imported successfully")
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    
    try:
        import app
        print("✓ Main application imported successfully")
    except ImportError as e:
        print(f"✗ Main application import error: {e}")
        return False
    
    return True

def test_structure():
    """Test that required files exist"""
    required_files = ['app.py', 'README.md', 'test_app.py']
    for file in required_files:
        if os.path.exists(file):
            print(f"✓ {file} exists")
        else:
            print(f"✗ {file} missing")
            return False
    return True

def test_functionality():
    """Test basic functionality"""
    try:
        import app
        # Check if main classes and functions exist
        if hasattr(app, 'Book') and hasattr(app, 'app'):
            print("✓ Application structure is correct")
        else:
            print("✗ Application structure is incorrect")
            return False
            
        # Check if database is properly configured
        if hasattr(app, 'db') and app.db:
            print("✓ Database configuration is correct")
        else:
            print("✗ Database configuration issue")
            return False
            
        return True
    except Exception as e:
        print(f"✗ Functionality test error: {e}")
        return False

if __name__ == '__main__':
    print("Verifying application structure and functionality...")
    
    success = True
    success &= test_imports()
    success &= test_structure()
    success &= test_functionality()
    
    if success:
        print("\n✓ All verifications passed!")
        sys.exit(0)
    else:
        print("\n✗ Some verifications failed!")
        sys.exit(1)