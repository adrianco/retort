# Book API REST Service

A REST API service for managing a book collection, built with Flask and SQLite.

## Features

- **POST /books** - Create a new book (title, author, year, isbn)
- **GET /books** - List all books (supports `?author=` filter)
- **GET /books/{id}** - Get a single book by ID
- **PUT /books/{id}** - Update a book
- **DELETE /books/{id}** - Delete a book
- **GET /health** - Health check endpoint

## Technical Details

- **Framework**: Flask
- **Database**: SQLite (embedded, no external server needed)
- **Response format**: JSON
- **Validation**: title and author are required fields

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

## Usage Examples

### Create a book

```bash
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "1984", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"}'
```

### List all books

```bash
curl http://localhost:5000/books
```

### List books by author

```bash
curl "http://localhost:5000/books?author=George%20Orwell"
```

### Get a single book

```bash
curl http://localhost:5000/books/1
```

### Update a book

```bash
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "1984 (Updated Edition)", "author": "George Orwell", "year": 1949}'
```

### Delete a book

```bash
curl -X DELETE http://localhost:5000/books/1
```

### Health check

```bash
curl http://localhost:5000/health
```

## Testing

Run the test suite:

```bash
pytest test_app.py -v
```

The tests cover:
- Health check endpoint
- Creating books (success and validation errors)
- Listing books (empty, with data, filtered by author)
- Getting a single book (success and not found)
- Updating a book (success, not found, validation errors)
- Deleting a book (success, not found)
