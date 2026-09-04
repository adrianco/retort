#!/usr/bin/env python3
"""
Test file for the Book API implementation.
This file shows how to test the API endpoints.
"""

import requests
import json

def test_book_api():
    """
    Test the Book API endpoints.
    """
    base_url = "http://127.0.0.1:3000"
    
    print("Testing Book API endpoints...")
    
    # Test 1: Health check
    print("\n1. Testing health check...")
    response = requests.get(f"{base_url}/health")
    print(f"Health check status: {response.status_code}")
    print(f"Health check response: {response.json()}")
    
    # Test 2: Create a book
    print("\n2. Creating a book...")
    book_data = {
        "title": "The Rust Programming Language",
        "author": "Steve Klabnik",
        "year": 2018,
        "isbn": "978-1731250050"
    }
    response = requests.post(f"{base_url}/books", json=book_data)
    print(f"Create book status: {response.status_code}")
    print(f"Created book: {response.json()}")
    
    # Store the created book ID for later tests
    book_id = response.json()['id']
    
    # Test 3: Get all books
    print("\n3. Getting all books...")
    response = requests.get(f"{base_url}/books")
    print(f"Get all books status: {response.status_code}")
    print(f"Books count: {len(response.json())}")
    
    # Test 4: Get a specific book
    print("\n4. Getting a specific book...")
    response = requests.get(f"{base_url}/books/{book_id}")
    print(f"Get book status: {response.status_code}")
    print(f"Book details: {response.json()}")
    
    # Test 5: Update a book
    print("\n5. Updating a book...")
    update_data = {
        "title": "The Rust Programming Language Updated",
        "author": "Steve Klabnik",
        "year": 2020,
        "isbn": "978-1731250051"
    }
    response = requests.put(f"{base_url}/books/{book_id}", json=update_data)
    print(f"Update book status: {response.status_code}")
    print(f"Updated book: {response.json()}")
    
    # Test 6: Filter books by author
    print("\n6. Filtering books by author...")
    response = requests.get(f"{base_url}/books?author=Rust")
    print(f"Filter books status: {response.status_code}")
    print(f"Filtered books count: {len(response.json())}")
    
    # Test 7: Delete a book
    print("\n7. Deleting a book...")
    response = requests.delete(f"{base_url}/books/{book_id}")
    print(f"Delete book status: {response.status_code}")
    
    # Test 8: Verify book deletion
    print("\n8. Verifying book deletion...")
    response = requests.get(f"{base_url}/books/{book_id}")
    print(f"Get deleted book status: {response.status_code}")
    print(f"Response: {response.json()}")

if __name__ == "__main__":
    test_book_api()