# Book Collection API

A small REST API for managing a book collection, written in Rust with
[axum](https://github.com/tokio-rs/axum) and an embedded
[SQLite](https://www.sqlite.org/) database (via `rusqlite` with the bundled
SQLite engine — no system SQLite required).

## Requirements

- Rust toolchain (edition 2021; tested with Rust 1.95). Install via
  [rustup](https://rustup.rs/).

## Setup & Run

```bash
# Build
cargo build --release

# Run (listens on 127.0.0.1:3000, data stored in ./books.db)
cargo run --release
```

Configuration via environment variables:

| Variable        | Default            | Description                                  |
| --------------- | ------------------ | -------------------------------------------- |
| `BIND_ADDR`     | `127.0.0.1:3000`   | Address the server binds to                  |
| `DATABASE_PATH` | `books.db`         | SQLite file path (use `:memory:` for in-RAM) |

Example:

```bash
BIND_ADDR=0.0.0.0:8080 DATABASE_PATH=/tmp/library.db cargo run --release
```

## API

A book is represented as:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593" }
```

`title` and `author` are required on create/update. `year` and `isbn` are
optional. All responses are JSON.

| Method   | Path           | Description                          | Success status |
| -------- | -------------- | ------------------------------------ | -------------- |
| `GET`    | `/health`      | Health check                         | `200`          |
| `POST`   | `/books`       | Create a book                        | `201`          |
| `GET`    | `/books`       | List books (`?author=` filter)       | `200`          |
| `GET`    | `/books/{id}`  | Get a book by id                     | `200`          |
| `PUT`    | `/books/{id}`  | Replace a book                       | `200`          |
| `DELETE` | `/books/{id}`  | Delete a book                        | `204`          |

Error responses: `400` for invalid input (missing/blank `title` or `author`),
`404` when a book id does not exist, both with a JSON body `{ "error": "..." }`.

### Examples

```bash
# Health
curl localhost:3000/health

# Create
curl -X POST localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'

# List, and filter by author
curl localhost:3000/books
curl 'localhost:3000/books?author=Frank%20Herbert'

# Get one
curl localhost:3000/books/1

# Update
curl -X PUT localhost:3000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'

# Delete
curl -X DELETE localhost:3000/books/1
```

## Tests

Integration tests exercise the router end-to-end against an in-memory database:

```bash
cargo test
```

They cover the health check, create/get, input validation, author filtering,
update/delete, and 404 handling.

## Project layout

```
src/
  main.rs       # binary entrypoint: opens DB, binds, serves
  lib.rs        # builds the axum Router
  handlers.rs   # HTTP handlers for each route
  db.rs         # SQLite-backed data access layer
  models.rs     # Book types and input validation
tests/
  api.rs        # integration tests
```
