# Book API REST Service

A REST API service for managing a book collection, built with Flask and SQLite.

## Features

- **POST /books** — Create a new book (title, author, year, isbn)
- **GET /books** — List all books (supports `?author=` filter)
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

### Get a book by ID

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

## Testing

Run the test suite:

```bash
python -m pytest test_app.py -v
```

## API Reference

### POST /books

Creates a new book.

**Request body (JSON):**

| Field  | Type   | Required | Description        |
|--------|--------|----------|--------------------|
| title  | string | Yes      | Book title         |
| author | string | Yes      | Book author        |
| year   | number | No       | Publication year   |
| isbn   | string | No       | ISBN number        |

**Response:** `201 Created` with the created book object.

### GET /books

Lists all books.

**Query parameters:**

| Parameter | Type   | Required | Description              |
|-----------|--------|----------|--------------------------|
| author    | string | No       | Filter by author (partial match) |

**Response:** `200 OK` with an array of book objects.

### GET /books/{id}

Gets a single book by ID.

**Response:** `200 OK` with the book object, or `404 Not Found`.

### PUT /books/{id}

Updates a book.

**Request body (JSON):** All fields are optional except `title` and `author`.

**Response:** `200 OK` with the updated book object, or `404 Not Found`.

### DELETE /books/{id}

Deletes a book.

**Response:** `200 OK` with a success message, or `404 Not Found`.

### GET /health

Health check endpoint.

**Response:** `200 OK` with `{"status": "healthy"}`.
