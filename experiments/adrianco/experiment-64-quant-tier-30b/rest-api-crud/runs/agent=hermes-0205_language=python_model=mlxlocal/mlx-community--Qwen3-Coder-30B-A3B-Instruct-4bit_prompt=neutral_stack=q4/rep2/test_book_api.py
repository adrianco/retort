import sqlite3
import os

# Create a working test file that demonstrates the API functionality
def test_book_api():
    """Create a test file that shows how to use the API"""
    test_content = """# Book API Test Script

This script demonstrates how to test the Book API.

## Setup
1. Run the application: `python app.py`
2. Use curl or any HTTP client to test the endpoints

## Example Usage:

### Health Check
curl http://localhost:5000/health

### Create a book
curl -X POST http://localhost:5000/books \\
  -H "Content-Type: application/json" \\
  -d '{"title": "Sample Book", "author": "Sample Author"}'

### Get all books
curl http://localhost:5000/books

### Get a specific book by ID
curl http://localhost:5000/books/1

### Update a book
curl -X PUT http://localhost:5000/books/1 \\
  -H "Content-Type: application/json" \\
  -d '{"title": "Updated Book Title", "author": "Updated Author"}'

### Delete a book
curl -X DELETE http://localhost:5000/books/1

"""
    
    with open('test_book_api.md', 'w') as f:
        f.write(test_content)

if __name__ == '__main__':
    test_book_api()