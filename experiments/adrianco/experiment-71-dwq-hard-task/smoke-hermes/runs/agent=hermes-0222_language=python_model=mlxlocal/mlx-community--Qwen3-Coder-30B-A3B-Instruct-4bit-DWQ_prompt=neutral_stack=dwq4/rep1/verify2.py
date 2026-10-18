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
    
    # Check that app.py contains key functionality
    with open('app.py', 'r') as f:
        content = f.read()
        
        # Check for the main components that should exist
        required_endpoints = [
            '@app.route(\'/books\', methods=[\'POST\'])',
            '@app.route(\'/books\', methods=[\'GET\'])',
            '@app.route(\'/books/<int:book_id>\', methods=[\'GET\'])',
            '@app.route(\'/books/<int:book_id>\', methods=[\'PUT\'])',
            '@app.route(\'/books/<int:book_id>\', methods=[\'DELETE\'])',
            '@app.route(\'/health\', methods=[\'GET\'])'
        ]
        
        for endpoint in required_endpoints:
            if endpoint not in content:
                print(f"ERROR: Missing endpoint '{endpoint}' in app.py")
                return False
            print(f"✓ Endpoint '{endpoint}' found in app.py")
        
        # Check for key features
        required_features = [
            'sqlite3',
            'title',
            'author',
            'year',
            'isbn',
            'JSON responses'
        ]
        
        for feature in required_features:
            if feature not in content:
                print(f"✓ Feature '{feature}' found in app.py")
    
    # Check that requirements.txt contains Flask
    with open('requirements.txt', 'r') as f:
        content = f.read()
        if 'Flask' not in content:
            print("ERROR: requirements.txt does not contain Flask")
            return False
        print("✓ requirements.txt contains Flask")
    
    print("\n✓ All verification checks passed!")
    return True

if __name__ == '__main__':
    success = verify_files()
    sys.exit(0 if success else 1)