# Book API

A REST API for managing a book collection, built with [axum](https://github.com/tokio-rs/axum) and SQLite (via `rusqlite` with the bundled SQLite engine — no system SQLite required).

## Requirements

- Rust (stable) and Cargo

## Run

```sh
cargo run
```

The server listens on `0.0.0.0:3000` by default and stores data in `books.db` in the working directory. Both are configurable via environment variables:

```sh
BIND_ADDR=127.0.0.1:8080 BOOKS_DB=/tmp/books.db cargo run
```

Use `BOOKS_DB=:memory:` for an ephemeral in-memory database.

## Test

```sh
cargo test
```

## API

| Method | Path          | Description                                  |
|--------|---------------|----------------------------------------------|
| GET    | `/health`     | Health check, returns `{"status":"ok"}`      |
| POST   | `/books`      | Create a book — returns `201` with the book  |
| GET    | `/books`      | List all books; filter with `?author=...`    |
| GET    | `/books/{id}` | Get a book by ID                             |
| PUT    | `/books/{id}` | Update a book (full replace)                 |
| DELETE | `/books/{id}` | Delete a book — returns `204`                |

A book has `title` (required), `author` (required), `year` (optional integer), and `isbn` (optional string). Missing or blank `title`/`author` returns `400` with `{"error": "..."}`; an unknown ID returns `404`.

### Examples

```sh
# Create
curl -X POST localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}'

# List, optionally filtered by author
curl 'localhost:3000/books?author=Frank%20Herbert'

# Get / update / delete by ID
curl localhost:3000/books/1
curl -X PUT localhost:3000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965}'
curl -X DELETE localhost:3000/books/1
```
