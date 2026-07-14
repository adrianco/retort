# Book Collection API

A small REST API for managing a book collection, built in **Rust** with
[axum](https://github.com/tokio-rs/axum) and **SQLite** (via `rusqlite` with the
bundled SQLite engine — no system dependency required).

## Requirements

- Rust (stable, edition 2021) and Cargo. Install via [rustup](https://rustup.rs/).

## Setup & Run

```bash
# Build
cargo build --release

# Run (creates ./books.db on first start)
cargo run --release
```

The server listens on `http://127.0.0.1:3000` by default.

Environment variables:

| Variable        | Default            | Description                          |
| --------------- | ------------------ | ------------------------------------ |
| `BIND_ADDR`     | `127.0.0.1:3000`   | Address the server binds to          |
| `DATABASE_PATH` | `books.db`         | Path to the SQLite database file     |

## API

A `Book` is JSON of the form:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593" }
```

`year` and `isbn` are optional; `title` and `author` are required.

| Method   | Path           | Description                              | Success status |
| -------- | -------------- | ---------------------------------------- | -------------- |
| `GET`    | `/health`      | Health check                             | `200`          |
| `POST`   | `/books`       | Create a book                            | `201`          |
| `GET`    | `/books`       | List books (optional `?author=` filter)  | `200`          |
| `GET`    | `/books/{id}`  | Get a single book                        | `200`          |
| `PUT`    | `/books/{id}`  | Replace/update a book                    | `200`          |
| `DELETE` | `/books/{id}`  | Delete a book                            | `204`          |

Error responses are JSON: `{ "error": "..." }`. Validation failures return
`400 Bad Request`; unknown IDs return `404 Not Found`.

### Examples

```bash
# Health
curl http://127.0.0.1:3000/health

# Create
curl -X POST http://127.0.0.1:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'

# List (all) and filtered by author
curl http://127.0.0.1:3000/books
curl 'http://127.0.0.1:3000/books?author=Frank%20Herbert'

# Get one
curl http://127.0.0.1:3000/books/1

# Update
curl -X PUT http://127.0.0.1:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'

# Delete
curl -X DELETE http://127.0.0.1:3000/books/1
```

## Tests

Integration tests live in `tests/api.rs` and exercise the router directly using
an in-memory SQLite database (no network or external DB needed):

```bash
cargo test
```

Covered: health check, create + fetch, required-field validation, the
`?author=` list filter, update + delete, and 404 handling.
