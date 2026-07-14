#!/usr/bin/env python3
"""
Demo script showing the book API in action
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def demo():
    print("=== Book Collection API Demo ===\n")
    
    # Health check
    print("1. Health Check:")
    response = requests.get(f"{BASE_URL}/health")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}\n")
    
    # Create books
    print("2. Creating Books:")
    books = [
        {
            "title": "1984",
            "author": "George Orwell",
            "year": 1948,
            "isbn": "978-0-452-28423-4"
        },
        {
            "title": "Animal Farm",
            "author": "George Orwell",
            "year": 1945,
            "isbn": "978-0-452-28424-1"
        },
        {
            "title": "To Kill a Mockingbird",
            "author": "Harper Lee",
            "year": 1960,
            "isbn": "978-0-06-112008-4"
        }
    ]
    
    for i, book in enumerate(books, 1):
        response = requests.post(f"{BASE_URL}/books", json=book)
        print(f"   Book {i} created: {response.json()['title']} (ID: {response.json()['id']})")
    
    print()
    
    # List all books
    print("3. All Books:")
    response = requests.get(f"{BASE_URL}/books")
    for book in response.json():
        print(f"   - {book['title']} by {book['author']} ({book['year']}) - ID: {book['id']}")
    print()
    
    # List books filtered by author
    print("4. Books by George Orwell:")
    response = requests.get(f"{BASE_URL}/books?author=George%20Orwell")
    for book in response.json():
        print(f"   - {book['title']} ({book['year']})")
    print()
    
    # Get a single book
    print("5. Get single book:")
    response = requests.get(f"{BASE_URL}/books/1")
    book = response.json()
    print(f"   Book ID 1: {book['title']} by {book['author']}")
    print()
    
    # Update a book
    print("6. Update a book:")
    update_data = {
        "title": "Nineteen Eighty-Four",
        "author": "George Orwell",
        "year": 1948,
        "isbn": "978-0-452-28423-4"
    }
    response = requests.put(f"{BASE_URL}/books/1", json=update_data)
    updated_book = response.json()
    print(f"   Updated: {updated_book['title']}")
    print()
    
    # Delete a book
    print("7. Delete a book:")
    response = requests.delete(f"{BASE_URL}/books/3")
    print(f"   Status: {response.status_code}")
    print("   Book deleted successfully")
    print()
    
    # Show remaining books
    print("8. Remaining books:")
    response = requests.get(f"{BASE_URL}/books")
    for book in response.json():
        print(f"   - {book['title']} by {book['author']} ({book['year']})")
    print("\n=== Demo Complete ===")

if __name__ == "__main__":
    demo()