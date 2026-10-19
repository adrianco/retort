# Book API

A REST API for managing a book collection, written in Java with an embedded
SQLite database.

## Stack

- **Java 17+** (built-in `com.sun.net.httpserver` HTTP server)
- **SQLite** via `sqlite-jdbc`
- **Jackson** for JSON
- **Maven** for build and tests
- **JUnit 5** for tests

## Setup

Requires a JDK (17 or newer) and Maven on your PATH.

```sh
mvn package
```

This compiles the code, runs the test suite, and produces
`target/book-api-1.0.0.jar`.

## Run

```sh
java -jar target/book-api-1.0.0.jar
```

The server listens on port **8080** by default and stores data in
`books.db` (created in the current directory on first run).

Configuration:

| Setting | Env var   | CLI arg | Default    |
|---------|-----------|---------|------------|
| Port    | `PORT`    | 1st     | `8080`     |
| DB file | `BOOK_DB` | 2nd     | `books.db` |

Example: `PORT=9000 java -jar target/book-api-1.0.0.jar`

## Endpoints

| Method | Path             | Description                                  | Success |
|--------|------------------|----------------------------------------------|---------|
| GET    | `/health`        | Health check                                 | 200     |
| POST   | `/books`         | Create a book                                | 201     |
| GET    | `/books`         | List all books (optional `?author=` filter)  | 200     |
| GET    | `/books/{id}`    | Get a single book                            | 200     |
| PUT    | `/books/{id}`    | Update a book                                | 200     |
| DELETE | `/books/{id}`    | Delete a book                                | 204     |

### Book JSON shape

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "978-0441172719"
}
```

`title` and `author` are **required** on create and update. `year` and `isbn`
are optional (may be omitted or `null`).

On update, `year`/`isbn` are only replaced when provided; omitted values keep
the existing ones.

### Errors

Errors are returned as JSON with the appropriate status code:

```json
{ "error": "title is required" }
```

| Status | Meaning |
|--------|---------|
| 400    | Validation failure (missing/blank title or author, malformed JSON) |
| 404    | Book or route not found |
| 405    | Method not allowed (response includes an `Allow` header) |
| 500    | Internal server error |

## Examples

```sh
# Health check
curl http://localhost:8080/health

# Create a book
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'

# List all books
curl http://localhost:8080/books

# List books by author
curl 'http://localhost:8080/books?author=Frank%20Herbert'

# Get one book
curl http://localhost:8080/books/1

# Update a book
curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966}'

# Delete a book
curl -X DELETE http://localhost:8080/books/1
```

## Tests

```sh
mvn test
```

Three test classes cover the API end-to-end:

- `BookApiIntegrationTest` — boots the real HTTP server on an ephemeral port
  with a throwaway SQLite DB and exercises every endpoint (create, list +
  author filter, get, update, delete, validation errors, 404/405).
- `BookStoreTest` — unit tests for the SQLite repository (CRUD, author
  filtering, update semantics, delete reporting).
- `BookValidationTest` — unit tests for input validation and JSON parsing
  (required fields, trimming, malformed JSON, unknown fields).
