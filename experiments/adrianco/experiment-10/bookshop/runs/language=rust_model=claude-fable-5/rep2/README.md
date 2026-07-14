# Books API

A REST API service for managing a book collection, built with Rust, [Axum](https://github.com/tokio-rs/axum), and SQLite (via `rusqlite` with the bundled SQLite engine — no system SQLite required).

## Requirements

- Rust toolchain (1.80+ recommended) — install via [rustup](https://rustup.rs) or Homebrew.

## Setup & Run

```sh
cargo run
```

The server listens on `http://127.0.0.1:3000` and stores data in `books.db` in the working directory. Both are configurable via environment variables:

```sh
BIND_ADDR=0.0.0.0:8080 DATABASE_PATH=/tmp/books.db cargo run
```

## Run Tests

```sh
cargo test
```

Tests run against an in-memory SQLite database and cover the health check, CRUD round-trips, input validation, the author filter, and 404 handling.

## API

| Method | Path          | Description                                  |
|--------|---------------|----------------------------------------------|
| GET    | `/health`     | Health check                                 |
| POST   | `/books`      | Create a book                                |
| GET    | `/books`      | List all books (optional `?author=` filter)  |
| GET    | `/books/{id}` | Get a single book                            |
| PUT    | `/books/{id}` | Update a book (full replacement)             |
| DELETE | `/books/{id}` | Delete a book                                |

### Book fields

- `title` (string, **required**)
- `author` (string, **required**)
- `year` (integer, optional)
- `isbn` (string, optional)

`title` and `author` must be non-empty (whitespace-only values are rejected). Validation failures return `400` with a `details` array listing each problem.

### Status codes

- `200 OK` — successful reads and updates
- `201 Created` — book created
- `204 No Content` — book deleted
- `400 Bad Request` — validation failure or malformed JSON
- `404 Not Found` — no book with that ID

### Examples

```sh
# Health check
curl http://127.0.0.1:3000/health

# Create
curl -X POST http://127.0.0.1:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}'

# List (all, then filtered by author)
curl http://127.0.0.1:3000/books
curl 'http://127.0.0.1:3000/books?author=Frank%20Herbert'

# Get / Update / Delete by ID
curl http://127.0.0.1:3000/books/1
curl -X PUT http://127.0.0.1:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}'
curl -X DELETE http://127.0.0.1:3000/books/1
```

## Project layout

- `src/lib.rs` — router, handlers, validation, and SQLite schema/queries
- `src/main.rs` — server entry point
- `tests/api.rs` — integration tests (in-memory SQLite, no network needed)
