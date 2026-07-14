# Book Collection REST API

A REST API service for managing a book collection, built with Flask and SQLite.

## Features

- **POST /books** - Create a new book (title, author, year, isbn)
- **GET /books** - List all books (supports `?author=` filter parameter)
- **GET /books/{id}** - Get a single book by ID
- **PUT /books/{id}** - Update an existing book
- **DELETE /books/{id}** - Delete a book by ID
- **GET /health** - Health check endpoint

## Technical Details

- **Framework**: Flask (Python)
- **Database**: SQLite (embedded, no external server needed)
- **Response format**: JSON with appropriate HTTP status codes
- **Validation**: Title and author are required fields

## Setup and Run

### 1. Install dependencies

```bash
pip install flask pytest
```

Or use the requirements file:

```bash
pip install -r requirements.txt
```

### 2. Run the application

```bash
python app.py
```

The server will start on `http://localhost:5000`.

### 3. Run tests

```bash
python -m pytest test_app.py -v
```

## API Examples

### Create a book

```bash
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"}'
```

### List all books

```bash
curl http://localhost:5000/books
```

### List books by author

```bash
curl "http://localhost:5000/books?author=Fitzgerald"
```

### Get a single book

```bash
curl http://localhost:5000/books/1
```

### Update a book

```bash
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby (Updated)"}'
```

### Delete a book

```bash
curl -X DELETE http://localhost:5000/books/1
```

### Health check

```bash
curl http://localhost:5000/health
```

## Response Codes

| Code | Meaning                                    |
|------|--------------------------------------------|
| 200  | Success (GET, PUT, DELETE)                 |
| 201  | Created (POST)                             |
| 400  | Bad request - validation error             |
| 404  | Not found                                  |

## Files

- `app.py` - Main application with all API endpoints
- `test_app.py` - Comprehensive test suite (17 tests)
- `requirements.txt` - Python dependencies
- `README.md` - This file
