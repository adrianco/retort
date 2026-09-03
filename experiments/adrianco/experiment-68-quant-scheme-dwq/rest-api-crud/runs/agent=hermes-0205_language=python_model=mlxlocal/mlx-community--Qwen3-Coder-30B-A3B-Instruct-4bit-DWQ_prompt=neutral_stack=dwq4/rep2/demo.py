#!/usr/bin/env python3
"""
Simple demonstration script to show the Book API in action.
This script will:
1. Start the API server
2. Make some example requests
3. Show the responses
"""

import requests
import json
import time
import threading
from app import app

def demonstrate_api():
    print("=== Book API Demonstration ===\n")
    
    # Start the Flask app in a separate thread
    def run_app():
        app.run(debug=False, host='0.0.0.0', port=5000)
    
    # Start server in background
    server_thread = threading.Thread(target=run_app)
    server_thread.daemon = True
    server_thread.start()
    
    # Give the server a moment to start
    time.sleep(1)
    
    base_url = "http://localhost:5000"
    
    try:
        # 1. Health check
        print("1. Health Check:")
        response = requests.get(f"{base_url}/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}\n")
        
        # 2. Create a book
        print("2. Create a Book:")
        book_data = {
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "year": 1925,
            "isbn": "978-0-7432-7356-5"
        }
        
        response = requests.post(f"{base_url}/books", 
                               json=book_data)
        print(f"   Status: {response.status_code}")
        print(f"   Created Book: {response.json()}\n")
        
        book_id = response.json()['id']
        
        # 3. Get all books
        print("3. Get All Books:")
        response = requests.get(f"{base_url}/books")
        print(f"   Status: {response.status_code}")
        print(f"   Books: {response.json()}\n")
        
        # 4. Get a specific book by ID
        print("4. Get Book by ID:")
        response = requests.get(f"{base_url}/books/{book_id}")
        print(f"   Status: {response.status_code}")
        print(f"   Book: {response.json()}\n")
        
        # 5. Update the book
        print("5. Update Book:")
        update_data = {
            "title": "The Great Gatsby - Updated",
            "author": "F. Scott Fitzgerald",
            "year": 1926,
            "isbn": "978-0-7432-7356-6"
        }
        
        response = requests.put(f"{base_url}/books/{book_id}", 
                              json=update_data)
        print(f"   Status: {response.status_code}")
        print(f"   Updated Book: {response.json()}\n")
        
        # 6. Filter books by author
        print("6. Filter Books by Author:")
        response = requests.get(f"{base_url}/books?author=F. Scott Fitzgerald")
        print(f"   Status: {response.status_code}")
        print(f"   Filtered Books: {response.json()}\n")
        
        # 7. Delete the book
        print("7. Delete Book:")
        response = requests.delete(f"{base_url}/books/{book_id}")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}\n")
        
        # 8. Try to get the deleted book (should fail)
        print("8. Try to get deleted book:")
        response = requests.get(f"{base_url}/books/{book_id}")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}\n")
        
    except Exception as e:
        print(f"Error during demonstration: {e}")

if __name__ == "__main__":
    demonstrate_api()