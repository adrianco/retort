# Book API

A REST API service for managing a book collection, written in Rust
([axum](https://github.com/tokio-rs/axum) + [rusqlite](https://github.com/rusqlite/rusqlite)).
Data is stored in an embedded SQLite database — no external services required.

## Requirements

- Rust toolchain (`rustc` / `cargo`)

## Setup & Run

```sh
cargo build --release
./target/release/book-api
```

The server listens on `http://127.0.0.1:8000` by default and creates
`books.db` in the current directory on first run.

Configuration via environment variables:

| Variable   | Default    | Meaning                          |
|------------|------------|----------------------------------|
| `PORT`     | `8000`     | Port to listen on                |
| `BOOKS_DB` | `books.db` | Path to the SQLite database file |

Example:

```sh
PORT=3000 BOOKS_DB=/tmp/books.db cargo run
```

## API

### `GET /`

Service info (endpoint index).

### `GET /health`

Health check.

```
$ curl http://localhost:8000/health
{"status":"ok"}
```

### `POST /books` — create a book

Body fields: `title` (required, non-empty), `author` (required, non-empty),
`year` (optional integer, 1000–2100), `isbn` (optional string).

```
$ curl -s -X POST http://localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-17271-9"}'
{"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-17271-9"}
```

Returns `201 Created` with the new book (including its `id`).
Returns `400 Bad Request` with `{"error": "..."}` when `title`/`author` are
missing/blank or `year` is out of range.

### `GET /books` — list books

Supports an optional `?author=` filter (case-insensitive exact match).

```
$ curl -s 'http://localhost:8000/books?author=Frank Herbert'
[{"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-17271-9"}]
```

### `GET /books/{id}` — get one book

Returns `200` with the book, or `404` with `{"error": "book {id} not found"}`.

### `PUT /books/{id}` — update a book

Full replacement: `title` and `author` are required in the body, `year` and
`isbn` are optional (omitting them clears the field).
Returns `200` with the updated book, `400` on invalid input, `404` if the id
does not exist.

### `DELETE /books/{id}` — delete a book

Returns `204 No Content` on success, `404` if the id does not exist.

## Status codes

| Code | Meaning                                   |
|------|-------------------------------------------|
| 200  | Success (GET / PUT / health)              |
| 201  | Book created                              |
| 204  | Book deleted (no body)                    |
| 400  | Validation error / malformed JSON         |
| 404  | Book not found                            |
| 500  | Unexpected server error                   |

## Tests

Unit tests (input validation) live in `src/lib.rs`; integration tests that
drive the full HTTP stack against an in-memory SQLite database live in
`tests/api.rs`.

```sh
cargo test
```

## Project layout

```
Cargo.toml
src/main.rs    — entry point (binds TCP listener, serves the router)
src/lib.rs     — state, models, validation, handlers, router, unit tests
tests/api.rs   — end-to-end HTTP integration tests
```
