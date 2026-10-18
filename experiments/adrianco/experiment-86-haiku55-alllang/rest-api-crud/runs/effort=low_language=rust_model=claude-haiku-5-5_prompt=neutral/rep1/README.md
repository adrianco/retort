# Book Collection API

A small REST service for managing a book collection, written in Rust with
[axum](https://github.com/tokio-rs/axum) and an embedded SQLite database
([rusqlite](https://github.com/rusqlite/rusqlite), bundled — no system SQLite needed).

## Requirements

- Rust toolchain (stable, 2021 edition or later) — install via <https://rustup.rs>

## Setup

```sh
cargo build
```

## Run

```sh
cargo run
```

The server listens on `127.0.0.1:3000` and stores data in `books.db` in the
current directory. Both can be overridden:

| Variable        | Default          | Purpose                    |
| --------------- | ---------------- | -------------------------- |
| `BIND_ADDR`     | `127.0.0.1:3000` | Address to listen on       |
| `DATABASE_PATH` | `books.db`       | Path to the SQLite file    |

```sh
BIND_ADDR=0.0.0.0:8080 DATABASE_PATH=/var/lib/books.db cargo run
```

## Test

```sh
cargo test
```

## API

All requests and responses use JSON. Errors have the shape `{"error": "..."}`.

A book looks like:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593" }
```

`title` and `author` are required and must be non-blank. `year` (non-negative
integer) and `isbn` (digits, `-` and `X` only) are optional.

| Method   | Path          | Description                                  | Success            |
| -------- | ------------- | -------------------------------------------- | ------------------ |
| `GET`    | `/health`     | Health check                                 | `200`              |
| `POST`   | `/books`      | Create a book                                | `201` + book       |
| `GET`    | `/books`      | List books; `?author=` filters (case-insensitive exact match) | `200` + array |
| `GET`    | `/books/{id}` | Get one book                                 | `200` + book       |
| `PUT`    | `/books/{id}` | Replace a book (full body, same validation as create) | `200` + book |
| `DELETE` | `/books/{id}` | Delete a book                                | `204` (no body)    |

Status codes: `400` invalid or malformed body, `404` unknown id, `500` internal error.

### Examples

```sh
curl -i -X POST localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'

curl 'localhost:3000/books?author=Frank%20Herbert'

curl -X PUT localhost:3000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'

curl -i -X DELETE localhost:3000/books/1

curl localhost:3000/health
```

## Project layout

- `src/lib.rs` — models, validation, storage, routes and handlers
- `src/main.rs` — server entry point
- `tests/api.rs` — integration tests (run against an in-memory database)
