# Book Collection REST API

A simple REST API service for managing a book collection, built with Python and Flask.

## Features

- **POST /books** — Create a new book (title, author, year, isbn)
- **GET /books** — List all books (supports `?author=` filter)
- **GET /books/{id}** — Get a single book by ID
- **PUT /books/{id}** — Update a book
- **DELETE /books/{id}** — Delete a book
- **GET /health** — Health check endpoint

Data is stored in a SQLite database.

## Setup

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:

   ```bash
   python app.py
   ```

   The server will start on `http://localhost:5000`.

## Testing

Run the tests with pytest:

```bash
pip install pytest
pytest test_app.py -v
```

## API Examples

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
  -d '{"title": "1984 (Updated Edition)"}'
```

### Delete a book

```bash
curl -X DELETE http://localhost:5000/books/1
```

### Health check

```bash
curl http://localhost:5000/health
```
