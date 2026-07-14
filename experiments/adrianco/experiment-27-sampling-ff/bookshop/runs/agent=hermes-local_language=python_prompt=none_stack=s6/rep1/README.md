# Book API REST Service

A REST API service for managing a book collection, built with Flask and SQLite.

## Features

- **POST /books** — Create a new book (title, author, year, isbn)
- **GET /books** — List all books (support `?author=` filter)
- **GET /books/{id}** — Get a single book by ID
- **PUT /books/{id}** — Update a book
- **DELETE /books/{id}** — Delete a book
- **GET /health** — Health check endpoint

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run the application:

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

### List books by author

```bash
curl "http://localhost:5000/books?author=Fitzgerald"
```

### Get a book by ID

```bash
curl http://localhost:5000/books/1
```

### Update a book

```bash
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby (Updated Edition)"}'
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

Run the tests with pytest:

```bash
pip install pytest
pytest test_app.py -v
```

The test suite includes:
- Health check tests
- Create book tests (valid and invalid inputs)
- List books tests (empty, with data, filtered by author)
- Get single book tests (existing and non-existing)
- Update book tests (valid update, not found, validation errors)
- Delete book tests (existing and non-existing)
- Full CRUD lifecycle integration test
