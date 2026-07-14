Book Collection REST API
========================

A REST API service for managing a book collection, built with Flask and SQLite.

Endpoints
---------

- POST   /books          - Create a new book (title, author, year, isbn)
- GET    /books          - List all books (supports ?author= filter)
- GET    /books/{id}     - Get a single book by ID
- PUT    /books/{id}     - Update a book
- DELETE /books/{id}     - Delete a book
- GET    /health         - Health check

Setup
-----

1. Install dependencies::

    pip install -r requirements.txt

2. Run the application::

    python app.py

The API will be available at http://localhost:5000

Usage Examples
--------------

Create a book::

    curl -X POST http://localhost:5000/books \
      -H "Content-Type: application/json" \
      -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}'

List all books::

    curl http://localhost:5000/books

List books by author::

    curl "http://localhost:5000/books?author=Fitzgerald"

Get a book by ID::

    curl http://localhost:5000/books/1

Update a book::

    curl -X PUT http://localhost:5000/books/1 \
      -H "Content-Type: application/json" \
      -d '{"title":"Updated Title","author":"Updated Author"}'

Delete a book::

    curl -X DELETE http://localhost:5000/books/1

Health check::

    curl http://localhost:5000/health

Testing
-------

Run the test suite::

    pytest test_app.py -v
