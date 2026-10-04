# Books API

A REST API for managing a book collection, written in Rust with
[axum](https://github.com/tokio-rs/axum) and SQLite (via `rusqlite`, with
SQLite bundled — no system library needed).

## Requirements

- Rust toolchain (stable, 1.75 or newer) with `cargo`
- A C compiler (used to build the bundled SQLite)

## Run

```bash
cargo run --release
```

The server listens on `http://0.0.0.0:3000` and stores data in `books.db` in
the current directory. Both are configurable:

| Variable        | Default    | Description                  |
|-----------------|------------|------------------------------|
| `PORT`          | `3000`     | TCP port to listen on        |
| `DATABASE_PATH` | `books.db` | Path to the SQLite database  |

```bash
PORT=8080 DATABASE_PATH=/tmp/books.db cargo run --release
```

## Test

```bash
cargo test
```

The integration tests in `tests/api.rs` drive the router in-process against an
in-memory SQLite database, so they need no running server or files on disk.

## API

A book looks like:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719" }
```

`title` and `author` are required and must be non-blank. `year` (integer,
0–9999) and `isbn` (string) are optional and are `null` when absent.

| Method | Path          | Description                          | Success | Errors   |
|--------|---------------|--------------------------------------|---------|----------|
| GET    | `/health`     | Health check                         | 200     |          |
| POST   | `/books`      | Create a book                        | 201     | 400      |
| GET    | `/books`      | List books; optional `?author=` filter (exact match, case-insensitive) | 200 | |
| GET    | `/books/{id}` | Get one book                         | 200     | 400, 404 |
| PUT    | `/books/{id}` | Replace a book (same body as create) | 200     | 400, 404 |
| DELETE | `/books/{id}` | Delete a book                        | 204     | 400, 404 |

`PUT` is a full replacement: optional fields omitted from the body are reset
to `null`.

Errors are JSON:

```json
{ "error": "validation failed", "details": ["title is required"] }
```

### Examples

```bash
curl -X POST localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

curl localhost:3000/books
curl 'localhost:3000/books?author=Frank%20Herbert'
curl localhost:3000/books/1

curl -X PUT localhost:3000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966}'

curl -X DELETE localhost:3000/books/1
```

## Layout

- `src/main.rs` — server startup and configuration
- `src/lib.rs` — router, handlers, validation, error responses
- `src/db.rs` — SQLite schema and queries
- `tests/api.rs` — integration tests
