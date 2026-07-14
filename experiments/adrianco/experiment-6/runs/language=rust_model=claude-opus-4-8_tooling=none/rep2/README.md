# Book API

A small REST API for managing a book collection, written in Rust with
[axum](https://github.com/tokio-rs/axum) and backed by an embedded
[SQLite](https://www.sqlite.org/) database (via `rusqlite` with the bundled
SQLite engine — no system SQLite required).

## Requirements

- Rust (stable) and Cargo
- A C compiler (needed once to build the bundled SQLite). On macOS this is the
  Apple Command Line Tools; on Linux, `gcc`/`clang`.

## Setup & Run

```bash
# Build
cargo build --release

# Run (creates ./books.db on first start, listening on 127.0.0.1:3000)
cargo run --release
```

Configuration via environment variables:

| Variable        | Default          | Description                       |
| --------------- | ---------------- | --------------------------------- |
| `BIND_ADDR`     | `127.0.0.1:3000` | Address/port the server binds to. |
| `DATABASE_PATH` | `books.db`       | Path to the SQLite database file. |

Example:

```bash
BIND_ADDR=0.0.0.0:8080 DATABASE_PATH=/data/books.db cargo run --release
```

## Running the Tests

```bash
cargo test
```

The suite contains integration tests that exercise every endpoint (create, read,
list, filter, update, delete, validation errors, and 404s) against an in-memory
SQLite database, so they leave no files behind.

## Data Model

A book has the following fields:

| Field    | Type             | Required | Notes                  |
| -------- | ---------------- | -------- | ---------------------- |
| `id`     | integer          | —        | Assigned by the server |
| `title`  | string           | yes      | Must be non-empty      |
| `author` | string           | yes      | Must be non-empty      |
| `year`   | integer \| null  | no       |                        |
| `isbn`   | string  \| null  | no       |                        |

## Endpoints

All responses are JSON (except `204 No Content` on delete).

### `GET /health`

Health check.

```bash
curl http://127.0.0.1:3000/health
# 200 {"status":"ok"}
```

### `POST /books`

Create a book. `title` and `author` are required.

```bash
curl -X POST http://127.0.0.1:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'
# 201 {"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}
```

Missing/blank `title` or `author` returns `400`:

```json
{ "error": "title is required" }
```

### `GET /books`

List all books. Optional `?author=` filter.

```bash
curl http://127.0.0.1:3000/books
curl "http://127.0.0.1:3000/books?author=Frank%20Herbert"
# 200 [ ...books... ]
```

### `GET /books/{id}`

Fetch a single book.

```bash
curl http://127.0.0.1:3000/books/1
# 200 { ...book... }   or   404 {"error":"book not found"}
```

### `PUT /books/{id}`

Replace a book's fields. `title` and `author` are required.

```bash
curl -X PUT http://127.0.0.1:3000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"Dune (Revised)","author":"Frank Herbert","year":1965}'
# 200 { ...updated book... }   or   404 {"error":"book not found"}
```

### `DELETE /books/{id}`

Delete a book.

```bash
curl -X DELETE http://127.0.0.1:3000/books/1
# 204 (no body)   or   404 {"error":"book not found"}
```

## HTTP Status Codes

| Code             | When                                          |
| ---------------- | --------------------------------------------- |
| `200 OK`         | Successful read/list/update                   |
| `201 Created`    | Book created                                  |
| `204 No Content` | Book deleted                                  |
| `400 Bad Request`| Validation failure (missing title/author)     |
| `404 Not Found`  | Book id does not exist                        |

## Project Layout

```
src/
  lib.rs   # routes, handlers, DB access, and the integration tests
  main.rs  # binary entry point: opens the DB and serves over HTTP
```
