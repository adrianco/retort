# Books API

A small REST API for managing a book collection, written in Rust with [axum](https://github.com/tokio-rs/axum) and an embedded SQLite database (via `rusqlite`).

## Requirements

- Rust toolchain (stable, 1.75+). Install with [rustup](https://rustup.rs/).

## Setup & Run

```sh
# Build and run the server (creates ./books.db on first run)
cargo run --release
```

The server listens on `0.0.0.0:3000` by default. Configure via environment variables:

- `BIND_ADDR` — address to bind, e.g. `127.0.0.1:8080`
- `DATABASE_PATH` — path to the SQLite database file (default: `books.db`)
- `RUST_LOG` — log level, e.g. `info`, `debug`

Example:

```sh
BIND_ADDR=127.0.0.1:8080 DATABASE_PATH=./data.db RUST_LOG=info cargo run --release
```

## Endpoints

| Method | Path           | Description                                       |
| ------ | -------------- | ------------------------------------------------- |
| GET    | `/health`      | Health check, returns `{"status":"ok"}`           |
| POST   | `/books`       | Create a book                                     |
| GET    | `/books`       | List all books; supports `?author=Name` filter    |
| GET    | `/books/{id}`  | Get a single book                                 |
| PUT    | `/books/{id}`  | Update a book                                     |
| DELETE | `/books/{id}`  | Delete a book                                     |

### Book schema

```json
{
  "id": 1,
  "title": "The Pragmatic Programmer",
  "author": "Andy Hunt",
  "year": 1999,
  "isbn": "9780201616224"
}
```

`title` and `author` are required on `POST` and `PUT`. `year` and `isbn` are optional.

### Example requests

```sh
# Create
curl -sX POST http://localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"The Pragmatic Programmer","author":"Andy Hunt","year":1999,"isbn":"9780201616224"}'

# List
curl -s http://localhost:3000/books
curl -s 'http://localhost:3000/books?author=Andy%20Hunt'

# Get
curl -s http://localhost:3000/books/1

# Update
curl -sX PUT http://localhost:3000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"The Pragmatic Programmer, 20th Anniversary Edition","author":"Andy Hunt","year":2019}'

# Delete
curl -sX DELETE http://localhost:3000/books/1
```

### Status codes

- `200 OK` — successful GET/PUT/list
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — missing/invalid input (e.g. missing `title` or `author`)
- `404 Not Found` — book id does not exist
- `500 Internal Server Error` — database or unexpected error

## Tests

The integration test suite uses an in-memory SQLite database — no setup required.

```sh
cargo test
```
