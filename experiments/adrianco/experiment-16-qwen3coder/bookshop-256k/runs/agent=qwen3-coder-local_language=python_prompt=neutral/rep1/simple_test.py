#!/usr/bin/env python3
"""
Simple test script to verify the book API functionality
"""
import subprocess
import time
import requests
import json
import sys

def test_api():
    # Start the app
    print("Starting the book API server...")
    process = subprocess.Popen([sys.executable, 'app.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Give it a moment to start
    time.sleep(2)
    
    try:
        # Test health check
        print("Testing health check...")
        response = requests.get('http://localhost:5001/health')
        assert response.status_code == 200
        assert response.json()['status'] == 'healthy'
        print("✓ Health check passed")
        
        # Test creating a book
        print("Testing book creation...")
        book_data = {
            'title': 'Test Book',
            'author': 'Test Author',
            'year': 2023,
            'isbn': '1234567890'
        }
        response = requests.post('http://localhost:5001/books', 
                               json=book_data)
        assert response.status_code == 201
        book = response.json()
        book_id = book['id']
        print("✓ Book created successfully")
        
        # Test getting all books
        print("Testing getting all books...")
        response = requests.get('http://localhost:5001/books')
        assert response.status_code == 200
        books = response.json()
        assert len(books) >= 1
        print("✓ Retrieved all books successfully")
        
        # Test getting a specific book
        print("Testing getting a specific book...")
        response = requests.get(f'http://localhost:5001/books/{book_id}')
        assert response.status_code == 200
        retrieved_book = response.json()
        assert retrieved_book['title'] == 'Test Book'
        print("✓ Retrieved specific book successfully")
        
        # Test updating a book
        print("Testing book update...")
        updated_data = {
            'title': 'Updated Book',
            'author': 'Updated Author',
            'year': 2024,
            'isbn': '0987654321'
        }
        response = requests.put(f'http://localhost:5001/books/{book_id}', 
                              json=updated_data)
        assert response.status_code == 200
        updated_book = response.json()
        assert updated_book['title'] == 'Updated Book'
        print("✓ Book updated successfully")
        
        # Test deleting a book
        print("Testing book deletion...")
        response = requests.delete(f'http://localhost:5001/books/{book_id}')
        assert response.status_code == 200
        assert response.json()['message'] == 'Book deleted successfully'
        print("✓ Book deleted successfully")
        
        print("\n🎉 All tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        # Stop the server
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

if __name__ == '__main__':
    success = test_api()
    sys.exit(0 if success else 1)