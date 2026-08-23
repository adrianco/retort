Book Collection REST API
========================

A simple REST API service for managing a book collection, built with Python and Flask.

Endpoints
---------

- POST /books       - Create a new book (required: title, author)
- GET  /books       - List all books (optional: ?author= filter)
- GET  /books/<id>  - Get a single book by ID
- PUT  /books/<id>  - Update a book
- DELETE /books/<id> - Delete a book
- GET  /health      - Health check

Setup
-----

1. Install dependencies:

    pip install flask pytest

2. Run the application:

    python app.py

The API will be available at http://localhost:5000

Testing
-------

Run the test suite:

    pytest test_app.py -v

Example usage
-------------

    # Create a book
    curl -X POST http://localhost:5000/books \
      -H "Content-Type: application/json" \
      -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925}'

    # List all books
    curl http://localhost:5000/books

    # Filter by author
    curl "http://localhost:5000/books?author=Fitzgerald"

    # Get a single book
    curl http://localhost:5000/books/1

    # Update a book
    curl -X PUT http://localhost:5000/books/1 \
      -H "Content-Type: application/json" \
      -d '{"title":"The Great Gatsby (Updated)"}'

    # Delete a book
    curl -X DELETE http://localhost:5000/books/1

    # Health check
    curl http://localhost:5000/health
