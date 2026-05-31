# Books API

A REST API for managing a book collection, built with Rust, [Axum](https://github.com/tokio-rs/axum), and SQLite (via `rusqlite`).

## Requirements

- Rust toolchain (1.75+ recommended) — install via [rustup](https://rustup.rs/).

## Build & Run

```sh
cargo run --release
```

The service listens on `0.0.0.0:3000` by default and stores data in `books.db` in the working directory.

Environment variables:

- `BIND_ADDR` — bind address (default `0.0.0.0:3000`)
- `DATABASE_PATH` — SQLite file path, or `:memory:` for an in-memory store (default `books.db`)

## Endpoints

| Method | Path                  | Description                                      |
| ------ | --------------------- | ------------------------------------------------ |
| GET    | `/health`             | Health check — `{"status":"ok"}`                 |
| POST   | `/books`              | Create a book (`title`, `author` required)       |
| GET    | `/books`              | List books; supports `?author=` filter           |
| GET    | `/books/{id}`         | Fetch a single book                              |
| PUT    | `/books/{id}`         | Update a book (partial updates allowed)          |
| DELETE | `/books/{id}`         | Delete a book                                    |

### Book schema

```json
{
  "id": "uuid-string",
  "title": "string",
  "author": "string",
  "year": 2019,
  "isbn": "978-..."
}
```

`title` and `author` are required. `year` and `isbn` are optional.

### Status codes

- `200 OK` — successful read / update
- `201 Created` — book created
- `204 No Content` — book deleted
- `400 Bad Request` — missing/invalid input
- `404 Not Found` — book id not found
- `500 Internal Server Error` — database failure

### Examples

```sh
# Create
curl -sX POST localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"The Rust Programming Language","author":"Steve Klabnik","year":2019}'

# List
curl -s localhost:3000/books
curl -s 'localhost:3000/books?author=Steve%20Klabnik'

# Get
curl -s localhost:3000/books/<id>

# Update
curl -sX PUT localhost:3000/books/<id> \
  -H 'content-type: application/json' \
  -d '{"year":2020}'

# Delete
curl -sX DELETE localhost:3000/books/<id>
```

## Tests

```sh
cargo test
```

Integration tests live in `tests/integration_test.rs` and exercise the router against an in-memory SQLite database.
