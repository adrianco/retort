# book-api

A small REST API for managing a book collection, written in Rust with
[axum](https://github.com/tokio-rs/axum) and SQLite (via `rusqlite` with the
bundled SQLite engine, so no system SQLite install is needed).

## Requirements

- Rust toolchain 1.75+ (`cargo`, `rustc`). Install via https://rustup.rs
- A C compiler (for the bundled SQLite build). On macOS, Xcode command line tools
  are sufficient; on Debian/Ubuntu, `apt install build-essential`.

## Setup and run

```bash
cargo build --release
cargo run --release
```

The server listens on `http://0.0.0.0:3000` and stores data in `books.db` in the
current directory. Both can be overridden with environment variables:

| Variable        | Default    | Description                                   |
|-----------------|------------|-----------------------------------------------|
| `PORT`          | `3000`     | TCP port to listen on                         |
| `DATABASE_PATH` | `books.db` | Path to the SQLite file (`:memory:` for RAM)  |

Example:

```bash
PORT=8080 DATABASE_PATH=/tmp/books.db cargo run --release
```

Press `Ctrl+C` to stop the server gracefully.

## Running tests

```bash
cargo test
```

This runs unit tests (validation, database layer) and HTTP integration tests
that drive the router end-to-end against an in-memory SQLite database.

## API

All request and response bodies are JSON.

| Method | Path              | Description                              | Success |
|--------|-------------------|------------------------------------------|---------|
| GET    | `/health`         | Health check (verifies DB connectivity)  | 200     |
| POST   | `/books`          | Create a book                            | 201     |
| GET    | `/books`          | List books, optional `?author=` filter   | 200     |
| GET    | `/books/{id}`     | Get one book                             | 200     |
| PUT    | `/books/{id}`     | Replace a book's fields                  | 200     |
| DELETE | `/books/{id}`     | Delete a book                            | 204     |

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

`title` and `author` are required and must be non-blank. `year` (integer,
0–9999) and `isbn` (ISBN-10 or ISBN-13, hyphens and spaces allowed) are optional.
Optional fields are omitted from responses when null.

`PUT` is a full replacement: any optional field omitted from the request body is
cleared.

### Error responses

| Status | When                                            | Body                                                        |
|--------|-------------------------------------------------|-------------------------------------------------------------|
| 400    | Malformed JSON, or non-numeric `{id}`           | `{"error": "..."}`                                          |
| 404    | Book id does not exist                          | `{"error": "book 7 not found"}`                             |
| 422    | Validation failed                               | `{"error": "validation failed", "details": ["title is required"]}` |
| 500    | Unexpected database error                       | `{"error": "internal server error"}`                        |

### Examples

```bash
# Health
curl -s localhost:3000/health

# Create
curl -s -X POST localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'

# List all / filter by author (case-insensitive exact match)
curl -s localhost:3000/books
curl -s 'localhost:3000/books?author=Frank%20Herbert'

# Get one
curl -s localhost:3000/books/1

# Update
curl -s -X PUT localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'

# Delete
curl -s -i -X DELETE localhost:3000/books/1
```

## Project layout

```
src/
  main.rs      # binary: config from env, starts the server
  lib.rs       # builds the axum Router
  handlers.rs  # HTTP handlers
  models.rs    # Book types and input validation
  db.rs        # SQLite persistence (rusqlite)
  error.rs     # ApiError -> JSON response mapping
tests/
  api.rs       # HTTP integration tests
```
