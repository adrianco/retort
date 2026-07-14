# Book Collection REST API

A REST API service for managing a book collection using Python, Flask, and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Input validation (title and author are required)
- Health check endpoint
- SQLite database for data persistence

## Setup

### Prerequisites

- Python 3.7+
- pip (Python package manager)

### Installation

1. Install dependencies:

```bash
pip install flask
```

2. Run the application:

```bash
python app.py
```

The server will start on `http://localhost:5000`

## API Endpoints

### Health Check

```
GET /health
```

Returns the health status of the service.

### Books

```
GET /books
```

List all books. Supports `?author=` filter.

```
POST /books
```

Create a new book.

Request body:
```json
{
  "title": "Book Title",
  "author": "Author Name",
  "year": 2024,
  "isbn": "123-456-789"
}
```

```
GET /books/{id}
```

Get a single book by ID.

```
PUT /books/{id}
```

Update a book.

Request body:
```json
{
  "title": "Updated Title",
  "author": "Updated Author",
  "year": 2024,
  "isbn": "123-456-789"
}
```

```
DELETE /books/{id}
```

Delete a book by ID.

## Response Codes

- `200 OK` - Success
- `201 Created` - Resource created
- `400 Bad Request` - Invalid input
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

## Example Usage

### Create a book

```bash
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"}'
```

### Get all books

```bash
curl http://localhost:5000/books
```

### Get books by author

```bash
curl "http://localhost:5000/books?author=F.+Scott+Fitzgerald"
```

### Get a single book

```bash
curl http://localhost:5000/books/1
```

### Update a book

```bash
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby (Updated)", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"}'
```

### Delete a book

```bash
curl -X DELETE http://localhost:5000/books/1
```

### Health check

```bash
curl http://localhost:5000/health
```

## Running Tests

```bash
python -m pytest tests/test_api.py -v
```

## Project Structure

```
.
├── app.py          # Main Flask application
├── README.md       # This file
├── tests/          # Test files
│   └── test_api.py
└── books.db        # SQLite database (created on first run)
```
