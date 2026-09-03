# Book API Python REST Service Implementation

This skill implements a complete REST API service for managing a book collection in Python with Flask and SQLite database.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- Input validation
- JSON responses with appropriate HTTP status codes
- SQLite database storage

## Endpoints

- `POST /books` - Create a new book (title, author, year, isbn)
- `GET /books` - List all books (support ?author= filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check

## Implementation Details

The implementation uses:
- Python 3.6+
- Flask web framework
- SQLite3 via built-in sqlite3 module
- Embedded database in a local file (books.db)
- HTTP handlers for all endpoints
- Proper error handling and validation
- Unit tests for all functionality

## Usage

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the application:
   ```
   python app.py
   ```

3. The API will be available at `http://localhost:8080`

## Testing

The implementation includes unit tests covering:
- Health check endpoint
- Book creation with validation
- Book retrieval
- Book updates
- Book deletion
- Error handling