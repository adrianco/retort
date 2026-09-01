# books-api

A small REST service for managing a book collection, written in Rust with
[axum](https://github.com/tokio-rs/axum) and SQLite (via `rusqlite`, bundled so
no system SQLite is required).

## Requirements

- Rust toolchain (1.75+; install via [rustup](https://rustup.rs))
- A C compiler (used to build the bundled SQLite)

## Run

```sh
cargo run --release
```

The server listens on `http://0.0.0.0:3000` and stores data in `books.db` in
the working directory. Override with environment variables:

| Variable        | Default    | Meaning                       |
|-----------------|------------|-------------------------------|
| `PORT`          | `3000`     | TCP port to listen on         |
| `DATABASE_PATH` | `books.db` | SQLite file (`:memory:` works) |

## Test

```sh
cargo test
```

Tests run the router in-process against an in-memory SQLite database.

## API

| Method | Path                 | Description                              | Success |
|--------|----------------------|------------------------------------------|---------|
| GET    | `/health`            | Health check                             | 200     |
| POST   | `/books`             | Create a book                            | 201     |
| GET    | `/books`             | List books, optional `?author=` filter   | 200     |
| GET    | `/books/{id}`        | Fetch one book                           | 200     |
| PUT    | `/books/{id}`        | Replace a book                           | 200     |
| DELETE | `/books/{id}`        | Delete a book                            | 204     |

Book JSON shape:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719" }
```

`title` and `author` are required (non-blank); `year` (0–9999) and `isbn` are
optional. Errors:

- `400` malformed JSON body
- `404` unknown book id (`{"error": "book not found"}`)
- `422` validation failure (`{"error": "validation failed", "details": [...]}`)

Example:

```sh
curl -X POST localhost:3000/books -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl 'localhost:3000/books?author=Frank%20Herbert'
```
