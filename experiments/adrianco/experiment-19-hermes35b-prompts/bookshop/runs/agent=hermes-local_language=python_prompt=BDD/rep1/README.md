# Book API REST Service

A REST API service for managing a book collection, built with Flask and SQLite.

## Setup

1. Install dependencies:

```
pip install flask
```

2. Run the application:

```
python app.py
```

The server starts on `http://localhost:5000`.

## Database

Books are stored in a SQLite database (`books.db`). The schema is created automatically on first request.

## API Endpoints

### GET /health

Returns the service health status.

**Response:**

```json
{"status": "healthy"}
```

Status: 200 OK

### POST /books

Create a new book.

**Request body (JSON):**

| Field  | Required | Type   | Description            |
|--------|----------|--------|------------------------|
| title  | Yes      | string | Book title             |
| author | Yes      | string | Book author            |
| year   | No       | number | Publication year       |
| isbn   | No       | string | ISBN number            |

**Response (201 Created):**

```json
{
  "id": 1,
  "title": "1984",
  "author": "George Orwell",
  "year": 1949,
  "isbn": "978-0451524935"
}
```

### GET /books

List all books. Supports optional `?author=` filter (case-insensitive partial match).

**Examples:**

- `GET /books` -- all books
- `GET /books?author=Orwell` -- books by Orwell

**Response (200 OK):**

```json
[
  {"id": 1, "title": "1984", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"}
]
```

### GET /books/{id}

Get a single book by ID.

**Response (200 OK):**

```json
{"id": 1, "title": "1984", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"}
```

Returns 404 if the book does not exist.

### PUT /books/{id}

Update an existing book. Requires `title` and `author` in the body. Optional: `year`, `isbn`.

**Response (200 OK):** The updated book object.

Returns 404 if the book does not exist. Returns 400 if title or author are missing.

### DELETE /books/{id}

Delete a book by ID.

**Response (200 OK):**

```json
{"message": "Book deleted successfully"}
```

Returns 404 if the book does not exist.

## Testing

All tests are BDD-style acceptance tests organized as Given-When-Then scenarios.

```
python -m pytest test_app.py -v
```

### Test Coverage

19 scenarios covering:

- Health check endpoint
- Create: success (full data, minimal fields) and failure (missing title, missing author, empty body)
- List: empty catalogue, all books, filter by exact author, filter by partial author, no matches
- Get: valid ID, non-existent ID
- Update: successful update, non-existent ID, missing required field
- Delete: successful deletion, verification via list, non-existent ID

Each test uses an isolated SQLite database to prevent test interference.
