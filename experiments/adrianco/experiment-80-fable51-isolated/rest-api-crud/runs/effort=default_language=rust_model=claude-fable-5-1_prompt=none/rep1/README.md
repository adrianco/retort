# Books API

A REST API for managing a book collection, written in Rust with
[axum](https://github.com/tokio-rs/axum) and SQLite (via `rusqlite`, with SQLite
bundled — no system library needed).

## Requirements

- Rust toolchain (stable) with Cargo
- A C compiler (used to build the bundled SQLite)

## Run

```bash
cargo run --release
```

The server listens on `http://127.0.0.1:3000` by default. Configuration is via
environment variables:

| Variable        | Default     | Description                                   |
|-----------------|-------------|-----------------------------------------------|
| `HOST`          | `127.0.0.1` | Address to bind                               |
| `PORT`          | `3000`      | Port to listen on                             |
| `DATABASE_PATH` | `books.db`  | SQLite file (created if missing)              |

## Test

```bash
cargo test
```

The integration tests in `tests/api.rs` drive the router in-process against an
in-memory SQLite database.

## API

A book looks like:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

`title` and `author` are required and must be non-empty; `year` (0–9999) and
`isbn` are optional and returned as `null` when absent.

| Method | Path          | Description                              | Success | Errors        |
|--------|---------------|------------------------------------------|---------|---------------|
| GET    | `/health`     | Health check                             | 200     |               |
| POST   | `/books`      | Create a book                            | 201     | 400, 422      |
| GET    | `/books`      | List books; `?author=` filters (exact match) | 200 |               |
| GET    | `/books/{id}` | Get one book                             | 200     | 404           |
| PUT    | `/books/{id}` | Replace a book (all fields, same validation as create) | 200 | 400, 404, 422 |
| DELETE | `/books/{id}` | Delete a book                            | 204     | 404           |

Errors are JSON: `{"error": "..."}`. Validation failures return 422 with a
`details` array listing each problem; malformed JSON returns 400.

### Examples

```bash
curl -X POST localhost:3000/books -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl localhost:3000/books
curl 'localhost:3000/books?author=Frank%20Herbert'
curl -X PUT localhost:3000/books/1 -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -X DELETE localhost:3000/books/1
```
