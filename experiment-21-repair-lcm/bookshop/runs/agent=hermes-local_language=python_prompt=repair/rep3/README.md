# Book Collection REST API

A REST API service for managing a book collection, built with Flask and SQLite.

## Features

- POST /books - Create a new book (title, author, year, isbn)
- GET /books - List all books (support ?author= filter)
- GET /books/{id} - Get a single book by ID
- PUT /books/{id} - Update a book
- DELETE /books/{id} - Delete a book
- GET /health - Health check endpoint

## Setup

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. That is it - no database setup needed. The app creates and initialises its SQLite database automatically on first request.

## Run

```bash
python app.py
```

The server starts on `http://localhost:5000`.

To run with a different host or port:

```bash
FLASK_APP=app.py flask run --host=0.0.0.0 --port=8080
```

## Testing

Run the test suite with:

```bash
pytest test_app.py -v
```

Tests are automatically isolated (a temporary SQLite database is created and cleaned up for each run).

## API Examples

### Create a book

```bash
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"1984","author":"George Orwell","year":1949,"isbn":"978-0451524935"}'
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
  -d '{"title":"Nineteen Eighty-Four"}'
```

### Delete a book

```bash
curl -X DELETE http://localhost:5000/books/1
```

### Health check

```bash
curl http://localhost:5000/health
```
