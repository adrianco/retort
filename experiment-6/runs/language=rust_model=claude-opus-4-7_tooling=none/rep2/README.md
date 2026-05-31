# Book API

A small REST service for managing a book collection. Written in Rust with [Axum](https://github.com/tokio-rs/axum) and SQLite (via `rusqlite`, bundled).

## Requirements

- Rust 1.75+ (uses edition 2021)
- No system SQLite required — `rusqlite` is built with the `bundled` feature.

## Build

```sh
cargo build --release
```

## Run

```sh
cargo run --release
```

The server listens on `0.0.0.0:3000` by default. Override with environment variables:

- `BIND_ADDR` — host:port to bind (default `0.0.0.0:3000`)
- `DATABASE_PATH` — SQLite file path (default `books.db`, use `:memory:` for ephemeral)

```sh
BIND_ADDR=127.0.0.1:8080 DATABASE_PATH=/tmp/books.db cargo run --release
```

## Test

```sh
cargo test
```

## API

All responses are JSON. The `Book` shape is:

```json
{
  "id": "uuid",
  "title": "string",
  "author": "string",
  "year": 1965,
  "isbn": "string-or-null"
}
```

| Method | Path                  | Body / Query                 | Success | Errors |
| ------ | --------------------- | ---------------------------- | ------- | ------ |
| GET    | `/health`             | —                            | 200     | —      |
| POST   | `/books`              | `{title, author, year?, isbn?}` | 201     | 400 missing title/author |
| GET    | `/books`              | optional `?author=Name`      | 200     | —      |
| GET    | `/books/{id}`         | —                            | 200     | 404 |
| PUT    | `/books/{id}`         | `{title, author, year?, isbn?}` | 200     | 400 / 404 |
| DELETE | `/books/{id}`         | —                            | 204     | 404 |

### Examples

```sh
curl -X POST http://localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

curl http://localhost:3000/books
curl 'http://localhost:3000/books?author=Frank%20Herbert'
curl http://localhost:3000/books/<id>

curl -X PUT http://localhost:3000/books/<id> \
  -H 'content-type: application/json' \
  -d '{"title":"Dune (revised)","author":"Frank Herbert","year":1965}'

curl -X DELETE http://localhost:3000/books/<id>
```

## Layout

- `src/main.rs` — server bootstrap
- `src/lib.rs` — router wiring (exposed for tests)
- `src/handlers.rs` — request handlers and validation
- `src/db.rs` — SQLite access layer
- `src/models.rs` — request/response types
- `tests/api.rs` — integration tests using `tower::ServiceExt::oneshot` against an in-memory DB
