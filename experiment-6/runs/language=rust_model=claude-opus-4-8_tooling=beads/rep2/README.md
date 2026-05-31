# book-api

A small REST API for managing a book collection, written in Rust using
[axum](https://github.com/tokio-rs/axum) for HTTP and
[sqlx](https://github.com/launchbadge/sqlx) with an embedded **SQLite** database
for storage.

## Requirements

- Rust (stable) with Cargo — install via [rustup](https://rustup.rs/).

## Setup & run

```bash
# Build
cargo build

# Run the server (creates ./books.db automatically)
cargo run
```

The server listens on `0.0.0.0:3000` by default. You can override the
configuration with environment variables:

| Variable       | Default                      | Description                          |
| -------------- | ---------------------------- | ------------------------------------ |
| `BIND_ADDR`    | `0.0.0.0:3000`               | Address/port to listen on            |
| `DATABASE_URL` | `sqlite:books.db?mode=rwc`   | sqlx SQLite URL (use `sqlite::memory:` for an ephemeral DB) |

Example:

```bash
BIND_ADDR=127.0.0.1:8080 DATABASE_URL="sqlite:mybooks.db?mode=rwc" cargo run
```

## API

A `Book` is JSON-shaped as:

```json
{ "id": 1, "title": "...", "author": "...", "year": 2018, "isbn": "978..." }
```

`title` and `author` are **required** (must be non-blank). `year` and `isbn`
are optional.

| Method   | Path           | Description                                   | Success status |
| -------- | -------------- | --------------------------------------------- | -------------- |
| `GET`    | `/health`      | Health check                                  | `200 OK`       |
| `POST`   | `/books`       | Create a book                                 | `201 Created`  |
| `GET`    | `/books`       | List books; optional `?author=` filter        | `200 OK`       |
| `GET`    | `/books/{id}`  | Get one book                                  | `200 OK`       |
| `PUT`    | `/books/{id}`  | Update a book                                 | `200 OK`       |
| `DELETE` | `/books/{id}`  | Delete a book                                 | `204 No Content` |

Error responses use appropriate status codes (`400` for validation failures,
`404` when a book does not exist) with a JSON body `{ "error": "..." }`.

### Examples

```bash
# Create
curl -s -X POST localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"The Rust Programming Language","author":"Steve Klabnik","year":2018,"isbn":"9781593278281"}'

# List (optionally filtered by author)
curl -s localhost:3000/books
curl -s 'localhost:3000/books?author=Steve%20Klabnik'

# Get one
curl -s localhost:3000/books/1

# Update
curl -s -X PUT localhost:3000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"TRPL, 2nd ed.","author":"Steve Klabnik","year":2023}'

# Delete
curl -s -X DELETE localhost:3000/books/1
```

## Tests

Integration tests exercise the router end-to-end against an in-memory SQLite
database (no network or running server required):

```bash
cargo test
```

The suite covers the health check, create/get, validation, the author filter,
and the update/delete lifecycle.
