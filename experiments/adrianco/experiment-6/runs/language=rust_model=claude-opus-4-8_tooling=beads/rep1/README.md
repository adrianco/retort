# Book Collection API

A small REST API for managing a book collection, written in Rust with
[axum](https://github.com/tokio-rs/axum) and an embedded
[SQLite](https://www.sqlite.org/) database (via `rusqlite` with the bundled
SQLite engine — no external database to install).

## Requirements

- Rust (stable, edition 2021) and Cargo. Install via [rustup](https://rustup.rs/).

## Build

```sh
cargo build --release
```

## Run

```sh
cargo run
```

The server listens on `http://127.0.0.1:3000` by default and stores data in a
`books.db` file in the working directory. Both are configurable via environment
variables:

| Variable        | Default          | Description                                   |
| --------------- | ---------------- | --------------------------------------------- |
| `BIND_ADDR`     | `127.0.0.1:3000` | Address the HTTP server binds to.             |
| `DATABASE_PATH` | `books.db`       | SQLite file path (use `:memory:` for ephemeral). |

Example:

```sh
BIND_ADDR=0.0.0.0:8080 DATABASE_PATH=/tmp/books.db cargo run
```

## API

A book is JSON of the form:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593" }
```

`title` and `author` are required; `year` and `isbn` are optional and may be `null`.

| Method   | Path           | Description                              | Success status |
| -------- | -------------- | ---------------------------------------- | -------------- |
| `GET`    | `/health`      | Health check.                            | `200 OK`       |
| `POST`   | `/books`       | Create a book.                           | `201 Created`  |
| `GET`    | `/books`       | List books; optional `?author=` filter.  | `200 OK`       |
| `GET`    | `/books/{id}`  | Fetch one book by id.                    | `200 OK`       |
| `PUT`    | `/books/{id}`  | Replace a book.                          | `200 OK`       |
| `DELETE` | `/books/{id}`  | Delete a book.                           | `204 No Content` |

Errors return a JSON body `{ "error": "..." }` with an appropriate status:
`400 Bad Request` for validation failures, `404 Not Found` for unknown ids.

### Examples

```sh
# Create
curl -s -X POST localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

# List (all, or filtered by author)
curl -s localhost:3000/books
curl -s 'localhost:3000/books?author=Frank%20Herbert'

# Get one
curl -s localhost:3000/books/1

# Update
curl -s -X PUT localhost:3000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"Dune (Deluxe)","author":"Frank Herbert","year":1965}'

# Delete
curl -s -X DELETE localhost:3000/books/1 -i
```

## Test

```sh
cargo test
```

Integration tests live in `tests/api.rs` and exercise the router against an
in-memory database covering the health check, create/get, validation, the
`author` filter, update, delete, and the not-found path.
