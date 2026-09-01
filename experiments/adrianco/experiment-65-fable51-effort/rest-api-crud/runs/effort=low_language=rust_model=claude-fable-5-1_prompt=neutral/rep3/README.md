# book-api

A small REST service for managing a book collection, written in Rust with
[axum](https://github.com/tokio-rs/axum) and SQLite (via `rusqlite` with the
bundled SQLite engine, so no system SQLite install is needed).

## Setup

Requires a Rust toolchain (1.75+). Install via <https://rustup.rs>.

```sh
cargo build --release
```

## Run

```sh
cargo run --release
# book-api listening on http://0.0.0.0:3000 (db: books.db)
```

Environment variables:

| Variable        | Default    | Purpose                    |
|-----------------|------------|----------------------------|
| `PORT`          | `3000`     | TCP port to listen on      |
| `DATABASE_PATH` | `books.db` | SQLite file (created)      |

## Endpoints

| Method | Path                    | Description                              |
|--------|-------------------------|------------------------------------------|
| GET    | `/health`               | Health check, `{"status":"ok"}`          |
| POST   | `/books`                | Create a book (201)                      |
| GET    | `/books`                | List books, optional `?author=` filter   |
| GET    | `/books/{id}`           | Get one book (404 if missing)            |
| PUT    | `/books/{id}`           | Replace a book (400 invalid, 404 missing)|
| DELETE | `/books/{id}`           | Delete a book (204, 404 if missing)      |

Book JSON: `{"id": 1, "title": "...", "author": "...", "year": 1965, "isbn": "..."}`.
`title` and `author` are required and must be non-blank; `year` and `isbn` are optional.
Errors are returned as `{"error": "..."}`.

Example:

```sh
curl -X POST localhost:3000/books -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'
curl 'localhost:3000/books?author=Frank%20Herbert'
```

## Tests

```sh
cargo test
```

Integration tests in `tests/api.rs` exercise every endpoint against an
in-memory SQLite database.
