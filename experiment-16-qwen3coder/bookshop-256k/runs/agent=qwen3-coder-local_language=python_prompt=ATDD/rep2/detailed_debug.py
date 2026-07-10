#!/usr/bin/env python3
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

# Test creating a book step by step
print("Testing book creation...")
book_data = {"title": "1984", "author": "George Orwell", "year": 1948, "isbn": "978-0-452-28423-4"}

print("Sending POST request...")
response = client.post("/books", json=book_data)
print(f"Status code: {response.status_code}")
print(f"Full response: {response}")
print(f"Response text: {response.text}")
print(f"Response JSON: {response.json()}")

if "id" in response.json():
    print("ID found in response")
else:
    print("ID NOT found in response")
    
print("Testing database state...")
# Let's check if database has data
import sqlite3
conn = sqlite3.connect('books.db')
cursor = conn.cursor()
cursor.execute('SELECT * FROM books')
rows = cursor.fetchall()
print(f"Database rows: {rows}")
conn.close()
