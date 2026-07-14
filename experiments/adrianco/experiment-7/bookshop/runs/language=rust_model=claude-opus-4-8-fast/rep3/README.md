# Book Collection API

A small REST API for managing a book collection, written in Rust with
[axum](https://github.com/tokio-rs/axum) and an embedded
[SQLite](https://www.sqlite.org/) database (via `rusqlite` with the bundled
SQLite, so no system SQLite install is required).

## Requirements

- Rust (stable) and Cargo — install via [rustup](https://rustup.rs/)
- A C compiler (used to build the bundled SQLite) — present by default on macOS
  (Xcode Command Line Tools) and most Linux toolchains

## Setup & Run

```bash
# Build
cargo build --release

# Run (listens on 127.0.0.1:3000 by default, data stored in ./books.db)
cargo run --release
```

Configuration via environment variables:

| Variable        | Default          | Description                               |
| --------------- | ---------------- | ----------------------------------------- |
| `BIND_ADDR`     | `127.0.0.1:3000` | Address/port the server binds to          |
| `DATABASE_PATH` | `books.db`       | SQLite file path (use `:memory:` for RAM) |

Example:

```bash
BIND_ADDR=0.0.0.0:8080 DATABASE_PATH=/data/books.db cargo run --release
```

## API

All request and response bodies are JSON.

| Method   | Path           | Description                          | Success status |
| -------- | -------------- | ------------------------------------ | -------------- |
| `GET`    | `/health`      | Health check                         | `200`          |
| `POST`   | `/books`       | Create a book                        | `201`          |
| `GET`    | `/books`       | List books (`?author=` to filter)    | `200`          |
| `GET`    | `/books/{id}`  | Get a single book                    | `200`          |
| `PUT`    | `/books/{id}`  | Update a book                        | `200`          |
| `DELETE` | `/books/{id}`  | Delete a book                        | `204`          |

### Book object

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "978-0441013593"
}
```

`title` and `author` are required (and must be non-blank). `year` and `isbn`
are optional and may be `null`.

### Status codes

- `200 OK` — successful read/update
- `201 Created` — book created
- `204 No Content` — book deleted
- `400 Bad Request` — validation failed (missing `title`/`author`)
- `404 Not Found` — book id does not exist
- `500 Internal Server Error` — unexpected database error

Errors are returned as `{ "error": "message" }`.

## Examples

```bash
# Health check
curl http://127.0.0.1:3000/health

# Create a book
curl -X POST http://127.0.0.1:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'

# List all books
curl http://127.0.0.1:3000/books

# Filter by author
curl 'http://127.0.0.1:3000/books?author=Frank%20Herbert'

# Get one book
curl http://127.0.0.1:3000/books/1

# Update a book
curl -X PUT http://127.0.0.1:3000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'

# Delete a book
curl -X DELETE http://127.0.0.1:3000/books/1
```

## Tests

Integration tests exercise the full router against an in-memory database
(no network or external SQLite needed):

```bash
cargo test
```

The suite covers the health check, create/get, validation failures,
the author filter, update (including 404), and delete (including 404).

## Project layout

```
src/
  main.rs       # binary entrypoint: config, pool, serve
  lib.rs        # router wiring (build_app)
  db.rs         # connection pool + schema init
  models.rs     # Book, BookInput, validation
  handlers.rs   # request handlers
tests/
  api.rs        # integration tests
```
