# books-api

A small REST API for managing a book collection, written in Rust with
[Axum](https://github.com/tokio-rs/axum) and an embedded SQLite database
(via `rusqlite` with the bundled SQLite engine, so no system library is needed).

## Requirements

- Rust toolchain (1.75 or newer) with `cargo`

## Setup and run

```bash
cargo build --release
cargo run --release
```

The server starts on `http://127.0.0.1:3000` and stores data in `books.db`
in the working directory. Both are configurable via environment variables:

| Variable        | Default          | Purpose                                   |
|-----------------|------------------|-------------------------------------------|
| `BIND_ADDR`     | `127.0.0.1:3000` | Address and port to listen on             |
| `DATABASE_PATH` | `books.db`       | SQLite file path (`:memory:` for ephemeral) |

Example:

```bash
BIND_ADDR=0.0.0.0:8080 DATABASE_PATH=/var/lib/books.db cargo run --release
```

The schema is created automatically on startup.

## Running the tests

```bash
cargo test
```

This runs unit tests for the persistence layer and integration tests that
drive the full HTTP router against an in-memory database.

## API

All request and response bodies are JSON.

| Method   | Path                    | Description                          | Success |
|----------|-------------------------|--------------------------------------|---------|
| `GET`    | `/health`               | Health check (also pings the DB)     | `200`   |
| `POST`   | `/books`                | Create a book                        | `201`   |
| `GET`    | `/books`                | List books; optional `?author=` filter (case-insensitive exact match) | `200` |
| `GET`    | `/books/{id}`           | Fetch one book                       | `200`   |
| `PUT`    | `/books/{id}`           | Replace a book's fields              | `200`   |
| `DELETE` | `/books/{id}`           | Delete a book                        | `204`   |

### Book fields

| Field    | Type    | Required | Notes                                   |
|----------|---------|----------|-----------------------------------------|
| `title`  | string  | yes      | Must be non-blank                       |
| `author` | string  | yes      | Must be non-blank                       |
| `year`   | integer | no       | 0 to 9999 if present                    |
| `isbn`   | string  | no       | Unique across books; blank is treated as absent |

`PUT` is a full replacement: any optional field omitted from the body is cleared.

### Error responses

| Status | When                                                |
|--------|-----------------------------------------------------|
| `400`  | Malformed JSON, non-integer `id`, or validation failure |
| `404`  | No book with the given `id`                         |
| `409`  | `isbn` already belongs to another book              |
| `500`  | Unexpected database error                           |

Validation errors look like:

```json
{ "error": "validation failed", "details": ["title is required", "author is required"] }
```

Other errors use the shape `{ "error": "..." }`.

## Examples

```bash
# Create
curl -s -X POST localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'

# List, optionally filtered
curl -s localhost:3000/books
curl -s 'localhost:3000/books?author=Frank%20Herbert'

# Get one
curl -s localhost:3000/books/1

# Update (full replacement)
curl -s -X PUT localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'

# Delete
curl -s -i -X DELETE localhost:3000/books/1

# Health
curl -s localhost:3000/health
```

## Project layout

```
src/
  main.rs      # binary: reads env config, opens DB, starts server
  lib.rs       # router construction and shared AppState
  handlers.rs  # HTTP handlers for each route
  db.rs        # SQLite schema and CRUD queries (with unit tests)
  models.rs    # request/response types and input validation
  error.rs     # ApiError -> HTTP status/JSON mapping
tests/
  api.rs       # end-to-end integration tests over the router
```
