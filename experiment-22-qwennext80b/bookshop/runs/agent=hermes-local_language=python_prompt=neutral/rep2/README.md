# Book Collection REST API Service

A REST API service for managing a book collection using Python, Flask, and SQLite.

## Features

- Create, read, update, and delete books
- List all books with optional author filter
- Health check endpoint
- Input validation
- SQLite database for persistent storage

## Requirements

- Python 3.7+
- pip (Python package manager)

## Installation

1. Install dependencies:

```bash
pip install flask
```

2. Initialize the database (run once):

```bash
python -c "from app import init_db; init_db()"
```

## Usage

### Run the server

```bash
python app.py
```

The server will start on `http://localhost:5000`

### API Endpoints

#### Health Check
```bash
GET /health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00.000000"
}
```

#### List Books
```bash
GET /books
GET /books?author=Author%20Name
```

#### Get Single Book
```bash
GET /books/{id}
```

#### Create Book
```bash
POST /books
Content-Type: application/json

{
  "title": "Book Title",
  "author": "Author Name",
  "year": 2024,
  "isbn": "1234567890"
}
```

Response (201 Created):
```json
{
  "id": 1,
  "title": "Book Title",
  "author": "Author Name",
  "year": 2024,
  "isbn": "1234567890",
  "created_at": "2024-01-01T00:00:00.000000"
}
```

#### Update Book
```bash
PUT /books/{id}
Content-Type: application/json

{
  "title": "Updated Title",
  "author": "Updated Author",
  "year": 2025
}
```

#### Delete Book
```bash
DELETE /books/{id}
```

## Testing

Run the tests:

```bash
python -m pytest test_api.py -v
```

Tests include:
- Health check endpoint
- Create book with validation
- List books with author filter
- Get single book
- Update book
- Delete book
- Error handling (not found, validation errors)
