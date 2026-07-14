#!/usr/bin/env python3

import requests
import json

BASE_URL = "http://localhost:5001"

def test_health():
    print("Testing health check...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_books_operations():
    print("Testing book operations...")
    
    # Create a book
    book_data = {
        "title": "1984",
        "author": "George Orwell",
        "year": 1948,
        "isbn": "978-0-452-28423-4"
    }
    
    print("Creating a book...")
    response = requests.post(f"{BASE_URL}/books", json=book_data)
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        book = response.json()
        print(f"Created book with ID: {book['id']}")
        book_id = book['id']
    else:
        print(f"Error: {response.json()}")
        return
    
    # Get all books
    print("\nGetting all books...")
    response = requests.get(f"{BASE_URL}/books")
    print(f"Status: {response.status_code}")
    print(f"Books count: {len(response.json())}")
    
    # Get books by author
    print("\nGetting books by author...")
    response = requests.get(f"{BASE_URL}/books?author=George%20Orwell")
    print(f"Status: {response.status_code}")
    print(f"Books count: {len(response.json())}")
    
    # Get specific book
    print(f"\nGetting book with ID {book_id}...")
    response = requests.get(f"{BASE_URL}/books/{book_id}")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        book = response.json()
        print(f"Book title: {book['title']}")
        print(f"Book author: {book['author']}")
    
    # Update the book
    print(f"\nUpdating book with ID {book_id}...")
    update_data = {
        "title": "Nineteen Eighty-Four",
        "year": 1949
    }
    response = requests.put(f"{BASE_URL}/books/{book_id}", json=update_data)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        updated_book = response.json()
        print(f"Updated title: {updated_book['title']}")
        print(f"Updated year: {updated_book['year']}")
    
    # Delete the book
    print(f"\nDeleting book with ID {book_id}...")
    response = requests.delete(f"{BASE_URL}/books/{book_id}")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("Book deleted successfully")

if __name__ == "__main__":
    test_health()
    test_books_operations()