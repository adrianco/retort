# Books API

A REST API for managing a book collection, written in Rust with
[axum](https://github.com/tokio-rs/axum) and SQLite (via `rusqlite`, bundled — no
system SQLite needed).

## Setup and run

Requires a Rust toolchain (`cargo`) and a C compiler (for the bundled SQLite).

```bash
cargo run --release
```

The server listens on `http://0.0.0.0:3000` and stores data in `books.db`.
Both are configurable through environment variables:

| Variable        | Default    | Description               |
|-----------------|------------|---------------------------|
| `PORT`          | `3000`     | TCP port to listen on     |
| `DATABASE_PATH` | `books.db` | SQLite database file path |

## Endpoints

| Method | Path          | Description                              | Success |
|--------|---------------|------------------------------------------|---------|
| GET    | `/health`     | Health check                             | 200     |
| POST   | `/books`      | Create a book                            | 201     |
| GET    | `/books`      | List books (optional `?author=` filter)  | 200     |
| GET    | `/books/{id}` | Get one book                             | 200     |
| PUT    | `/books/{id}` | Replace a book                           | 200     |
| DELETE | `/books/{id}` | Delete a book                            | 204     |

Book fields: `title` (required), `author` (required), `year` (optional integer),
`isbn` (optional string). `PUT` is a full replacement, so omitted optional fields
become `null`. The `author` filter is an exact match.

Errors are JSON, e.g. `{"error": "book not found"}`:

- `400` — malformed JSON or wrong field types
- `404` — book does not exist
- `422` — validation failed (missing/blank `title` or `author`), with a `details` list

## Example

```bash
curl -X POST localhost:3000/books -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'localhost:3000/books?author=Frank%20Herbert'
curl localhost:3000/books/1
curl -X PUT localhost:3000/books/1 -H 'content-type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
curl -X DELETE localhost:3000/books/1
```

## Tests

```bash
cargo test
```

Integration tests in `tests/api.rs` exercise every endpoint against an in-memory
SQLite database.
