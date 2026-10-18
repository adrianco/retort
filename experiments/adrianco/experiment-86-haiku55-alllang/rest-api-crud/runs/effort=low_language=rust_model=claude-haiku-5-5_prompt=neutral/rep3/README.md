# Book Collection API

A small REST API for managing a book collection, built with Rust, [axum](https://crates.io/crates/axum), and SQLite (via `rusqlite`, bundled — no system SQLite required).

## Requirements

- Rust toolchain (stable, 1.75+) with `cargo`

## Setup and run

```sh
cargo build --release
cargo run
```

The server listens on port `3000` by default. Configure with environment variables:

| Variable        | Default     | Purpose                    |
|-----------------|-------------|----------------------------|
| `PORT`          | `3000`      | HTTP port                  |
| `BOOKS_DB_PATH` | `books.db`  | Path to the SQLite file    |

```sh
PORT=8080 BOOKS_DB_PATH=/tmp/books.db cargo run
```

## Running tests

```sh
cargo test
```

## Endpoints

| Method | Path          | Description                              | Success |
|--------|---------------|------------------------------------------|---------|
| POST   | `/books`      | Create a book                            | 201     |
| GET    | `/books`      | List books; optional `?author=` filter (case-insensitive exact match) | 200 |
| GET    | `/books/{id}` | Get one book                             | 200     |
| PUT    | `/books/{id}` | Replace a book's fields                  | 200     |
| DELETE | `/books/{id}` | Delete a book                            | 204     |
| GET    | `/health`     | Health check                             | 200     |

### Book fields

| Field    | Type    | Required | Notes                                  |
|----------|---------|----------|----------------------------------------|
| `title`  | string  | yes      | Non-blank after trimming               |
| `author` | string  | yes      | Non-blank after trimming               |
| `year`   | integer | no       | 0–9999                                 |
| `isbn`   | string  | no       | ISBN-10 or ISBN-13 (hyphens/spaces ok) |

### Examples

```sh
curl -i -X POST localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-17271-9"}'

curl 'localhost:3000/books?author=Frank%20Herbert'
curl localhost:3000/books/1
curl -X PUT localhost:3000/books/1 -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -i -X DELETE localhost:3000/books/1
curl localhost:3000/health
```

### Errors

Errors return JSON `{"error": "..."}`:

- `400` — malformed JSON body
- `422` — validation failed; includes `details` listing every problem
- `404` — book not found
- `500` — internal database error
