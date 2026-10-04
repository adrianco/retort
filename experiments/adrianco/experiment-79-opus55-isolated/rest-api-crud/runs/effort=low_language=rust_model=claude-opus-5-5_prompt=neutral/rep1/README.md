# Books API

A REST service for managing a book collection, written in Rust with
[axum](https://github.com/tokio-rs/axum) and SQLite (via `rusqlite`, bundled —
no system SQLite needed).

## Setup and run

Requires a recent stable Rust toolchain (and a C compiler for the bundled SQLite).

```bash
cargo run --release
```

The server listens on `http://0.0.0.0:3000`. Configuration via environment:

| Variable   | Default    | Meaning                                         |
|------------|------------|-------------------------------------------------|
| `PORT`     | `3000`     | Port to listen on                               |
| `BOOKS_DB` | `books.db` | SQLite file path (`:memory:` for non-persistent) |

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
| GET    | `/books`      | List books; optional `?author=` filter (exact, case-insensitive) | 200 |
| GET    | `/books/{id}` | Get one book                         | 200     |
| PUT    | `/books/{id}` | Replace a book                       | 200     |
| DELETE | `/books/{id}` | Delete a book                        | 204     |

Book JSON: `{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}`.
`title` and `author` are required and must be non-blank; `year` (integer) and `isbn` (string) are optional.
PUT is a full replacement: omitted optional fields become `null`.

Errors are JSON, `{"error": "..."}`:

- `400` — malformed JSON / wrong field types, or a non-integer id
- `404` — book not found
- `422` — validation failed (includes a `details` array)

## Example

```bash
curl -X POST localhost:3000/books -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'localhost:3000/books?author=Frank%20Herbert'
curl -X PUT localhost:3000/books/1 -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -X DELETE localhost:3000/books/1
```
