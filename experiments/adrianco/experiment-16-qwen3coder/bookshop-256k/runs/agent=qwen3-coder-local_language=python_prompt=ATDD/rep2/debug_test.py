#!/usr/bin/env python3
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

# Test creating a book
print("Creating a book...")
response = client.post('/books', json={
    'title': 'Test Book',
    'author': 'Test Author',
    'year': 2023,
    'isbn': '1234567890'
})

print(f"Status code: {response.status_code}")
print(f"Response: {response.json()}")
print(f"Response headers: {response.headers}")
