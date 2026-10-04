# Books API

A REST API for managing a book collection, written in Rust with
[axum](https://github.com/tokio-rs/axum) and SQLite (via `rusqlite`, bundled — no
system SQLite needed).

## Setup and run

Requires a Rust toolchain (`cargo`) and a C compiler (for the bundled SQLite).

```bash
cargo run --release
```

The server listens on `http://0.0.0.0:3000`. Configuration via environment:

| Variable        | Default    | Description               |
|-----------------|------------|---------------------------|
| `PORT`          | `3000`     | Port to listen on         |
| `DATABASE_PATH` | `books.db` | SQLite database file path |

## Endpoints

| Method | Path          | Description                          | Success |
|--------|---------------|--------------------------------------|---------|
| GET    | `/health`     | Health check                         | 200     |
| POST   | `/books`      | Create a book                        | 201     |
| GET    | `/books`      | List books (optional `?author=` exact-match filter) | 200 |
| GET    | `/books/{id}` | Get one book                         | 200     |
| PUT    | `/books/{id}` | Replace a book                       | 200     |
| DELETE | `/books/{id}` | Delete a book                        | 204     |

Book body: `{"title": "...", "author": "...", "year": 1965, "isbn": "..."}`.
`title` and `author` are required and must be non-empty; `year` and `isbn` are optional.

Errors are JSON, `{"error": "message"}`: 400 for invalid input (missing fields,
malformed JSON, non-numeric ID), 404 for an unknown book.

```bash
curl -X POST localhost:3000/books -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl 'localhost:3000/books?author=Frank%20Herbert'
```

## Tests

```bash
cargo test
```

Integration tests in `tests/api.rs` exercise every endpoint against an in-memory database.
