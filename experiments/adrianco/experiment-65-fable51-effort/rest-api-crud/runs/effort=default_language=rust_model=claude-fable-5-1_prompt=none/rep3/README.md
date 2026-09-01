# book-api

A small REST service for managing a book collection, written in Rust with
[Axum](https://github.com/tokio-rs/axum) and SQLite (via `rusqlite` with the
bundled SQLite engine, so no system library is needed).

## Requirements

- Rust 1.75 or newer (stable toolchain, `cargo` on your PATH)
- A C compiler (used once to build the bundled SQLite)

## Setup and run

```bash
cargo build --release
cargo run --release
```

The server listens on `http://0.0.0.0:3000` and stores data in `books.db` in
the working directory. Both can be changed with environment variables:

| Variable        | Default    | Meaning                                      |
|-----------------|------------|----------------------------------------------|
| `PORT`          | `3000`     | TCP port to listen on                        |
| `DATABASE_PATH` | `books.db` | SQLite file path (`:memory:` for ephemeral)  |

Example:

```bash
PORT=8080 DATABASE_PATH=/tmp/books.db cargo run --release
```

Press Ctrl-C to stop; the server shuts down gracefully.

## Run the tests

```bash
cargo test
```

The integration tests in `tests/api.rs` exercise every endpoint against an
in-memory SQLite database.

## API

All request and response bodies are JSON.

| Method   | Path              | Description                                | Success |
|----------|-------------------|--------------------------------------------|---------|
| `GET`    | `/health`         | Health check (also pings the database)     | `200`   |
| `POST`   | `/books`          | Create a book                              | `201`   |
| `GET`    | `/books`          | List books, optional `?author=` filter     | `200`   |
| `GET`    | `/books/{id}`     | Fetch one book                             | `200`   |
| `PUT`    | `/books/{id}`     | Replace a book's fields                    | `200`   |
| `DELETE` | `/books/{id}`     | Delete a book                              | `204`   |

### Book object

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441013593"
}
```

`POST` and `PUT` accept the same body without `id`. Validation rules:

- `title` and `author` are required and must not be blank.
- `year` is optional; if present it must be an integer between 0 and 9999.
- `isbn` is optional; if present it must contain 10 or 13 alphanumeric
  characters (hyphens are allowed) and must be unique across books.

The `?author=` filter on `GET /books` is an exact, case-insensitive match.

### Error responses

| Status | When                                                     |
|--------|----------------------------------------------------------|
| `400`  | Malformed JSON, non-numeric `{id}`, or validation failed |
| `404`  | No book with that id                                     |
| `409`  | ISBN already used by another book                        |
| `500`  | Unexpected server or database error                      |

Validation failures include a `details` array:

```json
{ "error": "validation failed", "details": ["title is required", "author is required"] }
```

### Examples

```bash
# Health
curl -s localhost:3000/health

# Create
curl -s -X POST localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

# List / filter
curl -s localhost:3000/books
curl -s 'localhost:3000/books?author=Frank%20Herbert'

# Get one
curl -s localhost:3000/books/1

# Update
curl -s -X PUT localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

# Delete
curl -s -i -X DELETE localhost:3000/books/1
```

## Project layout

```
src/
  main.rs      binary entry point: reads env, opens DB, serves
  lib.rs       builds the Axum router (`app`)
  handlers.rs  HTTP handlers
  db.rs        SQLite access layer
  models.rs    request/response types and validation
  error.rs     error type -> HTTP status/JSON mapping
tests/
  api.rs       integration tests
```
