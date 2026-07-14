# Book API REST Service

A simple REST API for managing a book collection, built with Python and Flask.

## Features

- **POST /books** - Create a new book (title, author, year, isbn)
- **GET /books** - List all books (with optional `?author=` filter)
- **GET /books/{id}** - Get a single book by ID
- **PUT /books/{id}** - Update an existing book
- **DELETE /books/{id}** - Delete a book
- **GET /health** - Health check endpoint

## Technical Details

- **Language**: Python 3
- **Framework**: Flask
- **Database**: SQLite (embedded, no external setup required)
- **Storage**: Data persists in `books.db` file

## Setup and Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   python app.py
   ```

3. The API will be available at `http://localhost:5000`

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

## API Response Format

All responses are in JSON format with appropriate HTTP status codes:

- `200 OK` - Success
- `201 Created` - Book created successfully
- `400 Bad Request` - Validation error or invalid input
- `404 Not Found` - Book not found
- `409 Conflict` - Duplicate ISBN

## Testing

Run the test suite:

```bash
pip install pytest
pytest test_app.py -v
```

The tests cover:
- Health check endpoint
- Create, read, update, delete operations (CRUD)
- Input validation (required fields, year range)
- Author filtering
- Duplicate ISBN handling
- Error cases (404, 400)
