# Book API

A REST API for managing a book collection, built with [axum](https://github.com/tokio-rs/axum) and SQLite (via `rusqlite` with a bundled SQLite, so no system SQLite is required).

## Requirements

- Rust toolchain (1.75+ recommended) — install via [rustup](https://rustup.rs)

## Run

```sh
cargo run
```

The server listens on `http://0.0.0.0:3000` by default and stores data in `books.db` in the working directory.

Environment variables:

| Variable        | Default    | Purpose                  |
|-----------------|------------|--------------------------|
| `PORT`          | `3000`     | HTTP listen port         |
| `DATABASE_PATH` | `books.db` | SQLite database file     |

## Test

```sh
cargo test
```

Tests run against an in-memory SQLite database and exercise every endpoint through the full HTTP stack.

## API

| Method | Path          | Description                                  |
|--------|---------------|----------------------------------------------|
| GET    | `/health`     | Health check — `{"status":"ok"}`             |
| POST   | `/books`      | Create a book — returns `201` with the book  |
| GET    | `/books`      | List books, optional `?author=` exact filter |
| GET    | `/books/{id}` | Get a book — `404` if not found              |
| PUT    | `/books/{id}` | Replace a book — `404` if not found          |
| DELETE | `/books/{id}` | Delete a book — `204`, `404` if not found    |

A book looks like:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719" }
```

`title` and `author` are required (non-blank); `year` and `isbn` are optional. Missing or blank required fields return `400` with `{"error": "..."}`.

### Examples

```sh
# Create
curl -s -X POST localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'

# List (optionally filtered by author)
curl -s 'localhost:3000/books?author=Frank%20Herbert'

# Get / update / delete by id
curl -s localhost:3000/books/1
curl -s -X PUT localhost:3000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl -s -X DELETE localhost:3000/books/1 -i
```
