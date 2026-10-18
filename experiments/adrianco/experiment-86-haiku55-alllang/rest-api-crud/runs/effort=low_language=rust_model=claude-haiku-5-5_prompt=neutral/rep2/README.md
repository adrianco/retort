# Book Collection API

A REST API for managing a book collection, written in Rust with [axum](https://github.com/tokio-rs/axum) and SQLite (via `rusqlite`, bundled so no system SQLite is needed).

## Prerequisites

- Rust toolchain (stable, 1.80+) via [rustup](https://rustup.rs)
- A C compiler (needed to build the bundled SQLite)

## Build, test, run

```sh
cargo build
cargo test
cargo run
```

The server listens on `http://localhost:3000` by default. Configure with environment variables:

| Variable        | Default     | Purpose                    |
|-----------------|-------------|----------------------------|
| `PORT`          | `3000`      | HTTP port                  |
| `DATABASE_PATH` | `books.db`  | SQLite file (created if missing) |

```sh
PORT=8080 DATABASE_PATH=/tmp/books.db cargo run
```

## Data model

| Field    | Type    | Required | Notes                          |
|----------|---------|----------|--------------------------------|
| `id`     | integer | —        | Assigned by the server         |
| `title`  | string  | yes      | Non-blank after trimming       |
| `author` | string  | yes      | Non-blank after trimming       |
| `year`   | integer | no       | Positive if provided           |
| `isbn`   | string  | no       | Blank values are stored as null |

## Endpoints

| Method | Path          | Description                                      | Success |
|--------|---------------|--------------------------------------------------|---------|
| POST   | `/books`      | Create a book                                    | 201 + book |
| GET    | `/books`      | List books; `?author=` filters (exact, case-insensitive) | 200 + array |
| GET    | `/books/{id}` | Get one book                                     | 200 + book |
| PUT    | `/books/{id}` | Replace a book's fields                          | 200 + book |
| DELETE | `/books/{id}` | Delete a book                                    | 204 |
| GET    | `/health`     | Health check                                     | 200 `{"status":"ok"}` |

### Examples

```sh
curl -i -X POST localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

curl 'localhost:3000/books?author=Frank%20Herbert'
curl localhost:3000/books/1
curl -X PUT localhost:3000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl -i -X DELETE localhost:3000/books/1
```

### Errors

Errors are returned as `{"error": "<message>"}`:

- `400` — malformed JSON or wrong field types
- `404` — book not found
- `422` — validation failure (e.g. missing `title` or `author`)
- `500` — internal/database error

## Tests

- `src/lib.rs` unit tests cover request validation.
- `tests/api.rs` integration tests exercise every endpoint through the router using an in-memory database.
