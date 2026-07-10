# Book Collection REST API

A REST API service for managing a book collection, built with Flask and SQLite.

## Features

- **POST /books** - Create a new book (title, author, year, isbn)
- **GET /books** - List all books (supports `?author=` filter)
- **GET /books/{id}** - Get a single book by ID
- **PUT /books/{id}** - Update a book
- **DELETE /books/{id}** - Delete a book
- **GET /health** - Health check endpoint

## Setup

1. Ensure Python 3.8+ is installed.

2. Install dependencies:

   ```bash
   pip install flask flask-sqlalchemy
   ```

3. Run the application:

   ```bash
   python app.py
   ```

   The API will be available at `http://localhost:5000`.

## Usage Examples

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

### Filter by author

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
     -d '{"title": "Updated Title"}'
   ```

### Delete a book

   ```bash
   curl -X DELETE http://localhost:5000/books/1
   ```

## Testing

Run the test suite:

   ```bash
   pytest test_app.py -v
   ```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/books` | Create a new book |
| GET | `/books` | List all books |
| GET | `/books/<id>` | Get a book by ID |
| PUT | `/books/<id>` | Update a book |
| DELETE | `/books/<id>` | Delete a book |

### Input Validation

- `title` is required (non-empty string)
- `author` is required (non-empty string)
- `year` must be an integer if provided
- `isbn` is optional

### Error Responses

All error responses return a JSON object with an `error` key and the appropriate HTTP status code (400 for validation errors, 404 for not found).
