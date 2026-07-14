# Book Collection REST API

A REST API service for managing a book collection, built with Flask and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Input validation (title and author are required)
- Health check endpoint
- SQLite persistent storage

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run the application:

```bash
python app.py
```

The API will be available at `http://localhost:5000`

## API Endpoints

### GET /health
Health check endpoint.

**Response:**
```json
{"status": "healthy"}
```

### POST /books
Create a new book.

**Request Body:**
```json
{
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0743273565"
}
```

- title (required)
- author (required)
- year (optional)
- isbn (optional)

**Response:**
```json
{
  "id": 1,
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0743273565"
}
```

### GET /books
List all books. Supports `?author=filter` query parameter.

**Response:**
```json
[
  {
    "id": 1,
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0743273565"
  }
]
```

### GET /books/{id}
Get a single book by ID.

### PUT /books/{id}
Update a book. Partial updates are supported.

### DELETE /books/{id}
Delete a book.

## Running Tests

```bash
pip install -r requirements.txt
pytest test_app.py -v
```
