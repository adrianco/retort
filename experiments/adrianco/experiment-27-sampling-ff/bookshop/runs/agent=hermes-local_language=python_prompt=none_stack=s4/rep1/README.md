# Book API REST Service

A REST API service for managing a book collection, built with Flask and SQLite.

## Features

- **POST /books** — Create a new book (title, author, year, isbn)
- **GET /books** — List all books (supports `?author=` filter)
- **GET /books/{id}** — Get a single book by ID
- **PUT /books/{id}** — Update a book
- **DELETE /books/{id}** — Delete a book
- **GET /health** — Health check endpoint

## Technical Details

- **Framework**: Flask (Python)
- **Database**: SQLite (embedded, no external dependencies)
- **Response format**: JSON
- **Validation**: Title and author are required fields

## Setup and Run

### 1. Install Dependencies

```bash
pip install flask pytest
```

### 2. Run the Application

```bash
python app.py
```

The API will be available at `http://localhost:5000`.

### 3. Run Tests

```bash
pytest test_app.py -v
```

## API Examples

### Create a Book

```bash
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "1984", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"}'
```

### List All Books

```bash
curl http://localhost:5000/books
```

### List Books by Author

```bash
curl "http://localhost:5000/books?author=Orwell"
```

### Get a Single Book

```bash
curl http://localhost:5000/books/1
```

### Update a Book

```bash
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "1984 (Special Edition)", "author": "George Orwell"}'
```

### Delete a Book

```bash
curl -X DELETE http://localhost:5000/books/1
```

### Health Check

```bash
curl http://localhost:5000/health
```

## Project Structure

```
app.py          — Main Flask application with all endpoints
test_app.py     — Comprehensive acceptance tests
README.md       — This file
books.db        — SQLite database (created automatically)
```
