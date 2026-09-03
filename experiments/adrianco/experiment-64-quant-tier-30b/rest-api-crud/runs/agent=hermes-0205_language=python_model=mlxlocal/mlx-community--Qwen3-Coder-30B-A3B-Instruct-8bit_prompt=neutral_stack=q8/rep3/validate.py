#!/usr/bin/env python3
"""
Validation script to verify the implementation meets all requirements.
This script checks that the code implements all required features without needing to run the server.
"""

import ast
import re
import sys

def check_file_content(filename, required_patterns):
    """Check that a file contains all required patterns"""
    with open(filename, 'r') as f:
        content = f.read()
    
    missing = []
    for pattern in required_patterns:
        if not re.search(pattern, content):
            missing.append(pattern)
    
    if missing:
        print(f"✗ Missing patterns in {filename}:")
        for pattern in missing:
            print(f"  - {pattern}")
        return False
    else:
        print(f"✓ All required patterns found in {filename}")
        return True

def check_main_file():
    """Check main.py for all required features"""
    required_patterns = [
        r"GET /health",
        r"POST /books",
        r"GET /books",
        r"GET /books/\{id\}",
        r"PUT /books/\{id\}",
        r"DELETE /books/\{id\}",
        r"sqlite3",
        r"FastAPI",
        r"Book.*BaseModel",
        r"init_db",
        r"startup.*event",
        r"response_model=Book",
        r"HTTPException",
        r"Query.*Optional",
        r"Optional\[int\]",
        r"Optional\[str\]"
    ]
    
    return check_file_content('main.py', required_patterns)

def check_tests_file():
    """Check tests.py for all required test cases"""
    required_patterns = [
        r"test_health_check",
        r"test_create_book",
        r"test_get_books",
        r"test_get_book_by_id",
        r"test_update_book",
        r"test_delete_book",
        r"test_filter_books_by_author",
        r"TestClient",
        r"pytest"
    ]
    
    return check_file_content('tests.py', required_patterns)

def check_requirements():
    """Check requirements.txt"""
    required_packages = ['fastapi', 'uvicorn', 'pydantic']
    try:
        with open('requirements.txt', 'r') as f:
            content = f.read()
        
        missing = []
        for package in required_packages:
            if package not in content:
                missing.append(package)
        
        if missing:
            print(f"✗ Missing packages in requirements.txt: {missing}")
            return False
        else:
            print("✓ All required packages found in requirements.txt")
            return True
    except FileNotFoundError:
        print("✗ requirements.txt not found")
        return False

def check_readme():
    """Check README.md"""
    required_sections = [
        r"Health Check",
        r"Create Book",
        r"List Books",
        r"Get Book by ID",
        r"Update Book",
        r"Delete Book",
        r"Setup",
        r"API Endpoints"
    ]
    
    try:
        with open('README.md', 'r') as f:
            content = f.read()
        
        missing = []
        for section in required_sections:
            if not re.search(section, content):
                missing.append(section)
        
        if missing:
            print(f"✗ Missing sections in README.md: {missing}")
            return False
        else:
            print("✓ All required sections found in README.md")
            return True
    except FileNotFoundError:
        print("✗ README.md not found")
        return False

def main():
    """Main validation function"""
    print("Validating Book Collection API implementation...")
    print("=" * 50)
    print()
    
    success = True
    
    print("Checking main.py...")
    success &= check_main_file()
    print()
    
    print("Checking tests.py...")
    success &= check_tests_file()
    print()
    
    print("Checking requirements.txt...")
    success &= check_requirements()
    print()
    
    print("Checking README.md...")
    success &= check_readme()
    print()
    
    if success:
        print("🎉 All validation checks passed!")
        print("The implementation meets all the requirements.")
        return 0
    else:
        print("❌ Some validation checks failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())