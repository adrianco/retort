#!/usr/bin/env python3
"""
Simple test to verify that the API works correctly.
"""

import subprocess
import time
import requests
import json
import signal
import os

def test_api():
    """Test that the API works correctly"""
    
    # Start the Flask application
    print("Starting Flask app...")
    process = subprocess.Popen(
        ['python3', 'app.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for the server to start
    time.sleep(2)
    
    base_url = "http://localhost:5000"
    
    try:
        # Test health check
        print("Testing health check...")
        response = requests.get(f"{base_url}/health")
        print(f"Health check: {response.status_code}")
        assert response.status_code == 200
        print("✓ Health check works")
        
        # Test creating a book
        print("Testing book creation...")
        book_data = {
            "title": "1984",
            "author": "George Orwell",
            "year": 1948,
            "isbn": "978-0451524935"
        }
        
        response = requests.post(f"{base_url}/books", json=book_data)
        print(f"Create book: {response.status_code}")
        assert response.status_code == 201
        created_book = response.json()
        print(f"✓ Created book: {created_book['title']}")
        
        # Test getting all books
        print("Testing getting all books...")
        response = requests.get(f"{base_url}/books")
        print(f"Get all books: {response.status_code}")
        assert response.status_code == 200
        books = response.json()
        assert len(books) == 1
        print("✓ Got all books")
        
        # Test getting a single book
        print("Testing getting single book...")
        response = requests.get(f"{base_url}/books/{created_book['id']}")
        print(f"Get single book: {response.status_code}")
        assert response.status_code == 200
        retrieved_book = response.json()
        assert retrieved_book['title'] == book_data['title']
        print("✓ Got single book correctly")
        
        # Test updating a book
        print("Testing updating book...")
        updated_data = {
            "title": "Nineteen Eighty-Four",
            "author": "George Orwell",
            "year": 1948,
            "isbn": "978-0451524935"
        }
        response = requests.put(f"{base_url}/books/{created_book['id']}", json=updated_data)
        print(f"Update book: {response.status_code}")
        assert response.status_code == 200
        updated_book = response.json()
        assert updated_book['title'] == updated_data['title']
        print("✓ Updated book correctly")
        
        # Test deleting a book
        print("Testing deleting book...")
        response = requests.delete(f"{base_url}/books/{created_book['id']}")
        print(f"Delete book: {response.status_code}")
        assert response.status_code == 200
        print("✓ Deleted book")
        
        # Test that book is actually deleted
        response = requests.get(f"{base_url}/books/{created_book['id']}")
        assert response.status_code == 404
        print("✓ Book properly deleted")
        
        print("\n🎉 All tests passed! API is working correctly.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise
    finally:
        # Clean up
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

if __name__ == "__main__":
    test_api()