# Book API REST Service

A REST API service for managing a book collection, built with Flask and SQLite.

## Features

- **POST /books** - Create a new book (title, author, year, isbn)
- **GET /books** - List all books (support ?author= filter)
- **GET /books/{id}** - Get a single book by ID
- **PUT /books/{id}** - Update a book
- **DELETE /books/{id}** - Delete a book
- **GET /health** - Health check endpoint

## Setup and Run

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the application

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
curl "http://localhost:5000/books?author=Orwell"
```

### Get a single book

```bash
curl http://localhost:5000/books/1
```

### Update a book

```bash
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "1984 (Updated Edition)", "author": "George Orwell"}'
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
pip install pytest
pytest test_app.py -v
```

## API Response Codes

- **200 OK** - Successful GET, PUT, DELETE
- **201 Created** - Successful POST (book created)
- **400 Bad Request** - Invalid input (missing required fields)
- **404 Not Found** - Book ID does not exist
