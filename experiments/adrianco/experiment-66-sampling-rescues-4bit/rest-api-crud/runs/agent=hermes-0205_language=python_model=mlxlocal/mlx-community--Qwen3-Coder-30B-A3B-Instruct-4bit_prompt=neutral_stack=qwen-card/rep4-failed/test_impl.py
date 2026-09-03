#!/usr/bin/env python3
import os

def test_file_exists():
    """Test that main.py file exists"""
    if os.path.exists("main.py"):
        print("✓ Main.py file exists")
        return True
    else:
        print("✗ Main.py file does not exist")
        return False

def test_main_content():
    """Check main.py content"""
    try:
        with open("main.py", "r") as f:
            content = f.read()
        
        required_elements = [
            "FastAPI", 
            "FastAPI",
            "sqlite3",
            "GET /health",
            "GET /books",
            "GET /books/{id}",
            "POST /books",
            "PUT /books/{id}",
            "DELETE /books/{id}"
        ]
        
        missing_elements = []
        for element in required_elements:
            if element not in content:
                missing_elements.append(element)
        
        if missing_elements:
            print(f"✗ Missing API elements: {missing_elements}")
            return False
        else:
            print("✓ API structure correct")
            return True
    except Exception as e:
        print(f"✗ Error reading main.py: {e}")
        return False

def main():
    """Run tests"""
    print("Running implementation tests...")
    print("=" * 50)
    
    tests = [
        test_file_exists,
        test_main_content
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
    
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed!")
        return True
    else:
        print("✗ Some tests failed")
        return False

if __name__ == "__main__":
    main()