# Book Collection API

A small REST API for managing a book collection, written in Rust with
[axum](https://github.com/tokio-rs/axum) and an embedded
[SQLite](https://www.sqlite.org/) database (via `rusqlite` with the bundled
SQLite engine — no system SQLite required).

## Requirements

- Rust (stable, 2021 edition) and Cargo

## Setup & Run

```bash
# Build
cargo build --release

# Run (defaults to 127.0.0.1:3000, data stored in ./books.db)
cargo run --release
```

Configuration via environment variables:

| Variable        | Default          | Description                          |
|-----------------|------------------|--------------------------------------|
| `BIND_ADDR`     | `127.0.0.1:3000` | Address the server binds to          |
| `DATABASE_PATH` | `books.db`       | Path to the SQLite database file     |

Example with overrides:

```bash
BIND_ADDR=0.0.0.0:8080 DATABASE_PATH=/data/books.db cargo run --release
```

## API

All responses are JSON. A book has the shape:

```json
{ "id": 1, "title": "Dune", "author": "Herbert", "year": 1965, "isbn": "9780441013593" }
```

`title` and `author` are required; `year` and `isbn` are optional.

| Method   | Path            | Description                          | Success status |
|----------|-----------------|--------------------------------------|----------------|
| `GET`    | `/health`       | Health check                         | `200 OK`       |
| `POST`   | `/books`        | Create a book                        | `201 Created`  |
| `GET`    | `/books`        | List books (`?author=` filter)       | `200 OK`       |
| `GET`    | `/books/{id}`   | Get one book                         | `200 OK`       |
| `PUT`    | `/books/{id}`   | Update a book                        | `200 OK`       |
| `DELETE` | `/books/{id}`   | Delete a book                        | `204 No Content` |

Error statuses:

- `400 Bad Request` — missing/empty `title` or `author`
- `404 Not Found` — no book with the given id

### Examples

```bash
# Health
curl localhost:3000/health

# Create
curl -X POST localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Herbert","year":1965,"isbn":"9780441013593"}'

# List all / filter by author
curl localhost:3000/books
curl 'localhost:3000/books?author=Herbert'

# Get one
curl localhost:3000/books/1

# Update
curl -X PUT localhost:3000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"Dune (Revised)","author":"Frank Herbert","year":1965}'

# Delete
curl -X DELETE localhost:3000/books/1
```

## Tests

Integration tests exercise every endpoint against an in-memory SQLite database
(no network or files required):

```bash
cargo test
```

Covered: health check, create + fetch, validation failures, author filtering,
update (including 404), and delete (including 404).

## Project layout

```
src/lib.rs           # models, DB schema, handlers, router (build_app)
src/main.rs          # binary entry point (server bootstrap)
tests/integration.rs # end-to-end HTTP tests
```
