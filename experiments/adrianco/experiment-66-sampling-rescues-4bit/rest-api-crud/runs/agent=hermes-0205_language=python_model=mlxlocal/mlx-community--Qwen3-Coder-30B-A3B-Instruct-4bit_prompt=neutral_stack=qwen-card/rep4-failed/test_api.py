#!/usr/bin/env python3
import sqlite3
import json
import subprocess
import requests
import time
import threading
import time

def test_api():
    """Test that the API works properly"""
    try:
        # Start the server in the background
        process = subprocess.Popen(
            ["uvicorn", "main:app", "--host", "localhost", "--port", "8000", "--reload"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for server to start
        time.sleep(2)
        
        # Test health endpoint
        health_response = requests.get("http://localhost:8000/health")
        print(f"Health check status: {health_response.status_code}")
        print(f"Health check response: {health_response.json()}")
        
        # Test creating a book
        book_data = {
            "title": "Test Book",
            "author": "Test Author",
            "year": 2020,
            "isbn": "1234567890"
        }
        
        create_response = requests.post("http://localhost:8000/books", json=book_data)
        print(f"Create book status: {create_response.status_code}")
        print(f"Create book response: {create_response.json()}")
        
        # Test getting all books
        all_books_response = requests.get("http://localhost:8000/books")
        print(f"Get all books status: {all_books_response.status_code}")
        print(f"Get all books response: {all_books_response.json()}")
        
        # Test getting a specific book by ID
        book_id = create_response.json()["id"]
        specific_book_response = requests.get(f"http://localhost:8000/books/{book_id}")
        print(f"Get specific book status: {specific_book_response.status_code}")
        print(f"Get specific book response: {specific_book_response.json()}")
        
        # Test updating a book
        update_data = {
            "title": "Updated Test Book",
            "author": "Updated Author",
            "year": 2021,
            "isbn": "1234567890"
        }
        
        update_response = requests.put(f"http://localhost:8000/books/{book_id}", json=update_data)
        print(f"Update book status: {update_response.status_code}")
        print(f"Update book response: {update_response.json()}")
        
        # Test deleting a book
        delete_response = requests.delete(f"http://localhost:8000/books/{book_id}")
        print(f"Delete book status: {delete_response.status_code}")
        print(f"Delete book response: {delete_response.json()}")
        
        # Stop the server
        process.terminate()
        process.wait()
        
        return True
    except Exception as e:
        print(f"Error testing API: {e}")
        return False

if __name__ == "__main__":
    test_api()