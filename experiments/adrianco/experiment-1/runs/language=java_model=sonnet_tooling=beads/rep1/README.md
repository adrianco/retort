# Book Collection REST API

A Spring Boot REST API for managing a book collection, backed by SQLite.

## Requirements

- Java 17+
- Maven 3.6+

## Setup & Run

```bash
mvn spring-boot:run
```

The server starts on port 8080. The SQLite database file `books.db` is created in the working directory.

## API Endpoints

### Health Check

```
GET /health
```

Response: `{"status": "ok"}`

### Create a Book

```
POST /books
Content-Type: application/json

{
  "title": "Clean Code",
  "author": "Robert Martin",
  "year": 2008,
  "isbn": "978-0132350884"
}
```

- `title` and `author` are required; returns 400 with field errors if missing.
- Returns 201 with the created book (including generated `id`).

### List All Books

```
GET /books
GET /books?author=Robert Martin
```

- Optional `?author=` filter (case-insensitive).
- Returns 200 with a JSON array of books.

### Get a Book by ID

```
GET /books/{id}
```

- Returns 200 with the book, or 404 if not found.

### Update a Book

```
PUT /books/{id}
Content-Type: application/json

{
  "title": "Updated Title",
  "author": "Updated Author",
  "year": 2024,
  "isbn": "..."
}
```

- Returns 200 with the updated book, or 404 if not found.

### Delete a Book

```
DELETE /books/{id}
```

- Returns 204 on success, or 404 if not found.

## Running Tests

```bash
mvn test
```

Tests use an in-memory SQLite database so they do not affect `books.db`.
