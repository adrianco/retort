#!/usr/bin/env python3

import requests
import json

# Base URL for the API
BASE_URL = "http://localhost:5000"

def test_api():
    print("Testing Book Collection API")
    print("=" * 40)
    
    # Test health check
    print("1. Testing health check...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    
    # Test creating a book
    print("\n2. Creating a book...")
    book_data = {
        "title": "1984",
        "author": "George Orwell",
        "year": 1948,
        "isbn": "978-0-452-28423-4"
    }
    response = requests.post(f"{BASE_URL}/books", 
                           json=book_data)
    print(f"   Status: {response.status_code}")
    book = response.json()
    print(f"   Created book ID: {book['id']}")
    
    # Test getting all books
    print("\n3. Getting all books...")
    response = requests.get(f"{BASE_URL}/books")
    print(f"   Status: {response.status_code}")
    books = response.json()
    print(f"   Number of books: {len(books)}")
    
    # Test getting a specific book
    print("\n4. Getting specific book...")
    response = requests.get(f"{BASE_URL}/books/{book['id']}")
    print(f"   Status: {response.status_code}")
    book = response.json()
    print(f"   Book title: {book['title']}")
    
    # Test updating a book
    print("\n5. Updating a book...")
    update_data = {
        "title": "Nineteen Eighty-Four",
        "year": 1949
    }
    response = requests.put(f"{BASE_URL}/books/{book['id']}", 
                          json=update_data)
    print(f"   Status: {response.status_code}")
    updated_book = response.json()
    print(f"   Updated title: {updated_book['title']}")
    
    # Test deleting a book
    print("\n6. Deleting a book...")
    response = requests.delete(f"{BASE_URL}/books/{book['id']}")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    
    print("\nAPI Demo completed!")

if __name__ == "__main__":
    test_api()