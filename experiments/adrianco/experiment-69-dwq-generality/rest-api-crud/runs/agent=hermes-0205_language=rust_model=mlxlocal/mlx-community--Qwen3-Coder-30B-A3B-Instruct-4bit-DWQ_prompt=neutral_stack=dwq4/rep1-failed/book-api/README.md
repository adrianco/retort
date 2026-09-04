# Book API REST Service Implementation

This project implements a REST API service for managing a book collection using Python and Flask.

## Features

- POST /books - Create a new book (title, author, year, isbn)
- GET /books - List all books (support ?author= filter)
- GET /books/{id} - Get a single book by ID
- PUT /books/{id} - Update a book
- DELETE /books/{id} - Delete a book
- GET /health - Health check endpoint

## Requirements

- Python 3.7+
- Flask
- Flask-SQLAlchemy
- SQLite (embedded in the application)

## Setup

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run the server: `python book_api.py`

## Usage Examples

```bash
# Create a book
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Rust Programming Language","author":"Steve Klabnik","year":2018,"isbn":"978-1731250050"}'

# Get all books
curl http://localhost:3000/books

# Get a specific book by ID
curl http://localhost:3000/books/1

# Update a book
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Rust Programming Language Updated","author":"Steve Klabnik","year":2020,"isbn":"978-1731250051"}'

# Delete a book
curl -X DELETE http://localhost:3000/books/1

# Health check
curl http://localhost:3000/health
```

## Implementation Details

The API uses the following technologies:
- Flask for the web framework
- SQLAlchemy with SQLite for database access
- JSON serialization/deserialization

All data is stored in an SQLite database file (books.db) in the current directory.