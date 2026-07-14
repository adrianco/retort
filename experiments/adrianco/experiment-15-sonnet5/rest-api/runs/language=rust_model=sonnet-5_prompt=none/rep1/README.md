# book-api

A REST API for managing a book collection, built with [Axum](https://github.com/tokio-rs/axum) and [SQLite](https://www.sqlite.org/) (via `rusqlite`).

## Requirements

- Rust (stable toolchain, edition 2021)

## Setup

```bash
cargo build
```

## Run

```bash
cargo run
```

By default the server listens on `0.0.0.0:3000` and stores data in a SQLite file `books.db` in the current directory (created automatically on first run).

Both can be overridden with environment variables:

```bash
BIND_ADDR=127.0.0.1:8080 DATABASE_PATH=/tmp/books.db cargo run
```

## API

### Health check

```
GET /health
```

Returns `200 OK` with `{"status": "ok"}`.

### Create a book

```
POST /books
Content-Type: application/json

{
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441013593"
}
```

`title` and `author` are required (non-empty); `year` and `isbn` are optional. Returns `201 Created` with the created book, or `400 Bad Request` if `title`/`author` are missing.

### List books

```
GET /books
GET /books?author=Frank+Herbert
```

Returns `200 OK` with a JSON array of books. The optional `author` query parameter filters by exact author match.

### Get a single book

```
GET /books/{id}
```

Returns `200 OK` with the book, or `404 Not Found` if no book exists with that ID.

### Update a book

```
PUT /books/{id}
Content-Type: application/json

{
  "title": "Dune Messiah",
  "author": "Frank Herbert",
  "year": 1969,
  "isbn": "9780441172696"
}
```

Returns `200 OK` with the updated book, `400 Bad Request` on invalid input, or `404 Not Found` if no book exists with that ID.

### Delete a book

```
DELETE /books/{id}
```

Returns `204 No Content` on success, or `404 Not Found` if no book exists with that ID.

## Tests

```bash
cargo test
```

Integration tests in `tests/api.rs` exercise the full request/response cycle (via `tower::ServiceExt::oneshot`) against an in-memory SQLite database, covering creation, validation errors, lookups, filtering, updates, deletes, and 404 handling.

## Project layout

- `src/main.rs` — process entry point: opens the database and starts the HTTP server
- `src/lib.rs` — builds the Axum router
- `src/handlers.rs` — request handlers for each endpoint
- `src/models.rs` — `Book` model and input validation
- `src/db.rs` — SQLite connection setup and schema
- `src/error.rs` — error type mapped to HTTP status codes
- `tests/api.rs` — integration tests
