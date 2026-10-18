#!/usr/bin/env python3
"""
Simple verification that the app.py file was created correctly
"""

import os
import sys

def verify_files():
    """Verify that all required files exist and have the right content"""
    
    # Check that all required files exist
    required_files = ['app.py', 'requirements.txt', 'README.md']
    
    for file in required_files:
        if not os.path.exists(file):
            print(f"ERROR: Required file {file} does not exist")
            return False
        print(f"✓ {file} exists")
    
    # Check that app.py contains required components
    with open('app.py', 'r') as f:
        content = f.read()
        
        required_components = [
            'from flask import Flask, request, jsonify',
            'POST /books',
            'GET /books',
            'GET /books/{id}',
            'PUT /books/{id}',
            'DELETE /books/{id}',
            'GET /health',
            'SQLite'
        ]
        
        for component in required_components:
            if component not in content:
                print(f"ERROR: Missing component '{component}' in app.py")
                return False
            print(f"✓ Component '{component}' found in app.py")
    
    # Check that requirements.txt contains Flask
    with open('requirements.txt', 'r') as f:
        content = f.read()
        if 'Flask' not in content:
            print("ERROR: requirements.txt does not contain Flask")
            return False
        print("✓ requirements.txt contains Flask")
    
    # Check that README.md contains the required sections
    with open('README.md', 'r') as f:
        content = f.read()
        required_sections = [
            'Book API REST Service',
            'Endpoints',
            'Setup',
            'Database'
        ]
        
        for section in required_sections:
            if section not in content:
                print(f"ERROR: Missing section '{section}' in README.md")
                return False
            print(f"✓ Section '{section}' found in README.md")
    
    print("\n✓ All verification checks passed!")
    return True

if __name__ == '__main__':
    success = verify_files()
    sys.exit(0 if success else 1)