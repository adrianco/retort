# Book Collection REST API

A REST API service for managing a book collection, built with Flask and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Input validation (title and author are required)
- Health check endpoint
- SQLite database for persistent storage

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

## Setup

1. Create a virtual environment (optional but recommended):

```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the Application

```bash
python app.py
```

The API will be available at `http://localhost:5000`

## API Endpoints

### Health Check

- `GET /health`

Returns:

```json
{"status": "healthy"}
```

### Books

- `POST /books` - Create a new book
  - Body (JSON): `{"title": "string", "author": "string", "year": number, "isbn": "string"}`
  - `title` and `author` are required
  - Returns 201 on success

- `GET /books` - List all books
  - Optional query parameter: `?author=filter` (partial match)
  - Returns 200 with array of books

- `GET /books/{id}` - Get a single book by ID
  - Returns 200 with book object or 404 if not found

- `PUT /books/{id}` - Update a book
  - Body (JSON): any combination of `title`, `author`, `year`, `isbn`
  - `title` and `author` are required
  - Returns 200 with updated book or 404 if not found

- `DELETE /books/{id}` - Delete a book
  - Returns 200 on success or 404 if not found

## Examples

Create a book:

```bash
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "1984", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"}'
```

List all books:

```bash
curl http://localhost:5000/books
```

List books by author:

```bash
curl "http://localhost:5000/books?author=Orwell"
```

Get a book by ID:

```bash
curl http://localhost:5000/books/1
```

Update a book:

```bash
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Nineteen Eighty-Four"}'
```

Delete a book:

```bash
curl -X DELETE http://localhost:5000/books/1
```

## Running Tests

```bash
pip install pytest
pytest test_app.py -v
```
