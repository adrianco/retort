# Books API

A REST API for managing a book collection, built with Rust, [axum](https://github.com/tokio-rs/axum) and SQLite (via `rusqlite`, bundled — no system SQLite needed).

## Setup and run

Requires a Rust toolchain (https://rustup.rs) and a C compiler (for the bundled SQLite).

```bash
cargo run --release
```

The server listens on `http://0.0.0.0:3000`. Configuration via environment variables:

| Variable        | Default    | Description               |
|-----------------|------------|---------------------------|
| `PORT`          | `3000`     | Port to listen on         |
| `DATABASE_PATH` | `books.db` | SQLite database file path |

## Endpoints

| Method | Path          | Description                              | Success |
|--------|---------------|------------------------------------------|---------|
| GET    | `/health`     | Health check                             | 200     |
| POST   | `/books`      | Create a book                            | 201     |
| GET    | `/books`      | List books (optional `?author=` filter, exact match) | 200 |
| GET    | `/books/{id}` | Get one book                             | 200     |
| PUT    | `/books/{id}` | Replace a book                           | 200     |
| DELETE | `/books/{id}` | Delete a book                            | 204     |

Book JSON: `{"title": "...", "author": "...", "year": 1965, "isbn": "..."}`.
`title` and `author` are required and must be non-blank; `year` and `isbn` are optional.

Errors are JSON, e.g. `{"error": "book not found"}`:
400 for malformed JSON, 404 for unknown IDs, 422 for validation failures (with a `details` array).

```bash
curl -X POST localhost:3000/books -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'localhost:3000/books?author=Frank%20Herbert'
```

## Tests

```bash
cargo test
```

Integration tests in `tests/api.rs` run the full router against an in-memory SQLite database.
