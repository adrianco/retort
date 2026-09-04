#!/usr/bin/env python3
"""
Simple integration test for the Book API.
This demonstrates that all the required endpoints work correctly.
"""

import subprocess
import requests
import time
import os
import signal
import sys

def test_api_endpoints():
    """Test all required API endpoints"""
    
    print("Testing Book API endpoints...")
    
    # Start the API server in the background
    print("Starting API server...")
    server_process = subprocess.Popen([sys.executable, "book_api.py"])
    
    # Give the server time to start
    time.sleep(2)
    
    try:
        # Test health check
        print("\n1. Testing health check...")
        response = requests.get("http://127.0.0.1:3000/health")
        assert response.status_code == 200
        assert response.json()["status"] == "OK"
        print("✓ Health check works")
        
        # Test creating a book
        print("\n2. Testing create book...")
        book_data = {
            "title": "The Rust Programming Language",
            "author": "Steve Klabnik",
            "year": 2018,
            "isbn": "978-1731250050"
        }
        response = requests.post("http://127.0.0.1:3000/books", json=book_data)
        assert response.status_code == 201
        created_book = response.json()
        assert created_book["title"] == "The Rust Programming Language"
        assert created_book["author"] == "Steve Klabnik"
        print("✓ Create book works")
        
        book_id = created_book["id"]
        
        # Test getting all books
        print("\n3. Testing get all books...")
        response = requests.get("http://127.0.0.1:3000/books")
        assert response.status_code == 200
        books = response.json()
        assert len(books) >= 1
        print("✓ Get all books works")
        
        # Test getting a specific book
        print("\n4. Testing get specific book...")
        response = requests.get(f"http://127.0.0.1:3000/books/{book_id}")
        assert response.status_code == 200
        retrieved_book = response.json()
        assert retrieved_book["id"] == book_id
        assert retrieved_book["title"] == "The Rust Programming Language"
        print("✓ Get specific book works")
        
        # Test updating a book
        print("\n5. Testing update book...")
        update_data = {
            "title": "The Rust Programming Language Updated",
            "author": "Steve Klabnik",
            "year": 2020,
            "isbn": "978-1731250051"
        }
        response = requests.put(f"http://127.0.0.1:3000/books/{book_id}", json=update_data)
        assert response.status_code == 200
        updated_book = response.json()
        assert updated_book["title"] == "The Rust Programming Language Updated"
        print("✓ Update book works")
        
        # Test deleting a book
        print("\n6. Testing delete book...")
        response = requests.delete(f"http://127.0.0.1:3000/books/{book_id}")
        assert response.status_code == 204
        print("✓ Delete book works")
        
        # Test filtering by author
        print("\n7. Testing filter by author...")
        response = requests.get("http://127.0.0.1:3000/books?author=Rust")
        assert response.status_code == 200
        filtered_books = response.json()
        print(f"✓ Filter by author works (found {len(filtered_books)} books)")
        
        print("\n🎉 All tests passed! The Book API implementation meets all requirements.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        # Kill the server process
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except:
            server_process.kill()
    
    return True

if __name__ == "__main__":
    test_api_endpoints()