# Book API

A REST API service for managing a book collection, built with **Rust** ([axum](https://github.com/tokio-rs/axum)) and **SQLite** ([rusqlite](https://github.com/rusqlite/rusqlite)).

## Requirements

- Rust (stable toolchain, `cargo` on your PATH)

## Setup

```bash
cargo build --release
```

SQLite is compiled and bundled with the crate (`rusqlite` with the `bundled` feature), so no system database is needed.

## Run

```bash
cargo run
# or the release binary:
./target/release/book-api
```

The server listens on port **8000** by default. Configuration via environment variables:

| Variable        | Default    | Description                          |
| --------------- | ---------- | ------------------------------------ |
| `PORT`          | `8000`     | TCP port to bind                     |
| `DATABASE_PATH` | `books.db` | Path to the SQLite database file     |

Example:

```bash
PORT=3000 DATABASE_PATH=/tmp/books.db cargo run
```

The database file and `books` table are created automatically on first start.

## API

All request and response bodies are JSON. Errors are returned as `{"error": "<message>"}` with the appropriate status code.

### `GET /`

Service descriptor (also used as the readiness probe target). Returns `200` with the service name, status, and endpoint list.

### `GET /health`

Liveness check. Returns `200` with `{"status": "ok"}`.

### `POST /books`

Create a book. `title` and `author` are **required** and must be non-empty; `year` and `isbn` are optional.

Returns `201` with the created book (including its generated `id`), or `400` if validation fails.

```bash
curl -s -X POST http://localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}'
# => {"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}
```

### `GET /books`

List all books, ordered by id. Supports an optional exact-match filter on the author:

```bash
curl -s 'http://localhost:8000/books?author=Frank%20Herbert'
# => [{"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}]
```

### `GET /books/{id}`

Fetch a single book. Returns `200` with the book, or `404` if it does not exist.

```bash
curl -s http://localhost:8000/books/1
```

### `PUT /books/{id}`

Update a book (partial update): only the fields present in the request body are changed; omitted fields keep their current values. When `title` or `author` is present it must be non-empty.

Returns `200` with the updated book, `400` on validation failure, or `404` if the book does not exist.

```bash
curl -s -X PUT http://localhost:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year": 1966}'
```

### `DELETE /books/{id}`

Delete a book. Returns `204` with an empty body on success, or `404` if the book does not exist.

```bash
curl -s -X DELETE http://localhost:8000/books/1 -o /dev/null -w '%{http_code}'
# => 204
```

## Status codes

| Code | Meaning                                        |
| ---- | ---------------------------------------------- |
| 200  | Success (GET, PUT)                             |
| 201  | Book created (POST)                            |
| 204  | Book deleted (DELETE, empty body)              |
| 400  | Invalid JSON or validation error (missing/empty `title` or `author`) |
| 404  | Book not found                                 |
| 500  | Unexpected database error                      |

## Tests

Run the unit and integration tests (the integration tests exercise the full HTTP stack against an in-memory SQLite database):

```bash
cargo test
```

## Project layout

```
Cargo.toml
src/
  main.rs          # entry point: config, DB init, server startup
  lib.rs           # models, validation, handlers, router, unit tests
tests/
  integration.rs   # end-to-end HTTP tests for every endpoint
```
