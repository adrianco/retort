# Books API

A REST API for managing a book collection, written in Rust using [axum](https://github.com/tokio-rs/axum) and SQLite (via `rusqlite` / `tokio-rusqlite`).

## Endpoints

| Method | Path          | Description                              |
| ------ | ------------- | ---------------------------------------- |
| GET    | `/health`     | Health check                             |
| POST   | `/books`      | Create a book                            |
| GET    | `/books`      | List books (optional `?author=` filter)  |
| GET    | `/books/{id}` | Get a book by ID                         |
| PUT    | `/books/{id}` | Update a book                            |
| DELETE | `/books/{id}` | Delete a book                            |

Book fields: `title` (required), `author` (required), `year`, `isbn`.

## Setup

Requires Rust (stable, 1.75+).

```bash
cargo build
```

## Run

```bash
cargo run
```

The server binds to `0.0.0.0:3000` by default. Override with env vars:

- `BIND_ADDR` — address to bind (default `0.0.0.0:3000`)
- `DATABASE_PATH` — SQLite file path (default `books.db`)

Example:

```bash
curl -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'

curl http://localhost:3000/books?author=Frank%20Herbert
```

## Tests

```bash
cargo test
```
