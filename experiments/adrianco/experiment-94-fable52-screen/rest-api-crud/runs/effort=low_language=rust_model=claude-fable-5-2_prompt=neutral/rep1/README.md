# Books API

A REST API for managing a book collection, written in Rust with
[axum](https://github.com/tokio-rs/axum) and SQLite (via `rusqlite`, bundled —
no system SQLite needed).

## Setup and run

Requires a recent stable Rust toolchain (and a C compiler, for bundled SQLite).

```bash
cargo run --release
```

The server listens on `http://0.0.0.0:3000` and stores data in `books.db`.
Both are configurable through environment variables:

| Variable        | Default    | Purpose                                   |
|-----------------|------------|-------------------------------------------|
| `PORT`          | `3000`     | TCP port                                  |
| `DATABASE_PATH` | `books.db` | SQLite file (`:memory:` for non-persistent) |

## Tests

```bash
cargo test
```

Integration tests in `tests/api.rs` drive the router against an in-memory database.

## Endpoints

| Method | Path          | Description                          | Success |
|--------|---------------|--------------------------------------|---------|
| GET    | `/health`     | Health check                         | 200     |
| POST   | `/books`      | Create a book                        | 201     |
| GET    | `/books`      | List books (`?author=` exact, case-insensitive filter) | 200 |
| GET    | `/books/{id}` | Get one book                         | 200     |
| PUT    | `/books/{id}` | Replace a book (full update)         | 200     |
| DELETE | `/books/{id}` | Delete a book                        | 204     |

Book body: `title` and `author` are required non-blank strings; `year` (integer)
and `isbn` (string) are optional.

Errors are JSON, `{"error": "..."}`:

- `400` — malformed JSON or non-numeric ID
- `404` — book not found
- `422` — validation failed (with a `details` array) or wrong field types

## Example

```bash
curl -X POST localhost:3000/books -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl 'localhost:3000/books?author=Frank%20Herbert'
curl -X PUT localhost:3000/books/1 -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -X DELETE localhost:3000/books/1
```
