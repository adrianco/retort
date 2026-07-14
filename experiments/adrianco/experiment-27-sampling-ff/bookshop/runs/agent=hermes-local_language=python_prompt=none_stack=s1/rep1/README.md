# Book API REST Service

A REST API service for managing a book collection, built with Flask and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Input validation with proper error handling
- SQLite database for persistent storage
- JSON responses with appropriate HTTP status codes

## Setup

1. Install dependencies:

```
pip install -r requirements.txt
```

2. Run the application:

```
python app.py
```

The API will be available at `http://localhost:5000`

## API Endpoints

### GET /health

Health check endpoint.

Response:
```json
{"status": "healthy"}
```

### POST /books

Create a new book.

Request body (JSON):
- `title` (required) - Title of the book
- `author` (required) - Author of the book
- `year` (optional) - Publication year
- `isbn` (optional) - ISBN number

Response:
```json
{"id": 1, "title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"}
```

### GET /books

List all books. Supports optional `?author=` query parameter for filtering.

Response:
```json
[{"id": 1, "title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"}]
```

### GET /books/{id}

Get a single book by ID.

Response:
```json
{"id": 1, "title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"}
```

### PUT /books/{id}

Update a book. Only provide the fields you want to update.

Response:
```json
{"id": 1, "title": "The Great Gatsby (Updated)", "author": "F. Scott Fitzgerald", "year": 1926, "isbn": "978-0743273565"}
```

### DELETE /books/{id}

Delete a book.

Response:
```json
{"message": "Book deleted successfully"}
```

## Testing

Run the test suite:

```
python -m pytest test_app.py -v
```

16 tests covering all CRUD operations, filtering, validation, and error handling.
