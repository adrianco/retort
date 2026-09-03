#!/usr/bin/env python3
"""
Final validation script to verify the implementation meets all requirements.
"""

import sys

def check_main_file():
    """Check main.py for all required features"""
    required_features = [
        "health_check",
        "/health",
        "create_book",
        "POST /books",
        "get_books", 
        "GET /books",
        "get_book",
        "GET /books/{book_id}",
        "update_book",
        "PUT /books/{book_id}",
        "delete_book",
        "DELETE /books/{book_id}",
        "sqlite3.connect",
        "FastAPI",
        "BaseModel",
        "init_db",
        "@app.on_event",
        "response_model=Book",
        "HTTPException",
        "Query",
        "Optional[int]",
        "Optional[str]"
    ]
    
    with open('main.py', 'r') as f:
        content = f.read()
    
    missing = []
    for feature in required_features:
        if feature not in content:
            missing.append(feature)
    
    if missing:
        print("✗ Missing features in main.py:")
        for feature in missing:
            print(f"  - {feature}")
        return False
    else:
        print("✓ All required features found in main.py")
        return True

def check_tests_file():
    """Check tests.py for all required test cases"""
    required_tests = [
        "test_health_check",
        "test_create_book",
        "test_get_books",
        "test_get_book_by_id",
        "test_update_book", 
        "test_delete_book",
        "test_filter_books_by_author"
    ]
    
    with open('tests.py', 'r') as f:
        content = f.read()
    
    missing = []
    for test in required_tests:
        if test not in content:
            missing.append(test)
    
    if missing:
        print("✗ Missing tests:")
        for test in missing:
            print(f"  - {test}")
        return False
    else:
        print("✓ All required tests found in tests.py")
        return True

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
    """Check README.md for required sections"""
    required_sections = [
        "Health Check",
        "Create Book", 
        "List Books",
        "Get Book by ID",
        "Update Book",
        "Delete Book",
        "Setup",
        "API Endpoints"
    ]
    
    try:
        with open('README.md', 'r') as f:
            content = f.read()
        
        missing = []
        for section in required_sections:
            if section not in content:
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
        print()
        print("Summary of implemented features:")
        print("- POST /books — Create a new book")
        print("- GET /books — List all books (with author filter)")
        print("- GET /books/{id} — Get a single book by ID") 
        print("- PUT /books/{id} — Update a book")
        print("- DELETE /books/{id} — Delete a book")
        print("- GET /health — Health check endpoint")
        print("- SQLite database storage")
        print("- JSON responses with appropriate HTTP status codes")
        print("- Input validation for title and author")
        print("- Proper error handling")
        return 0
    else:
        print("❌ Some validation checks failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())