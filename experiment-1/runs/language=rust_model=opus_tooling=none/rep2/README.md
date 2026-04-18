# books-api

REST API for managing a book collection, built with Rust, Axum, and SQLite (rusqlite, bundled).

## Setup

Requires Rust (stable). Dependencies are fetched by Cargo.

```
cargo build
```

## Run

```
cargo run
```

The server listens on `0.0.0.0:3000`. Data is stored in an in-memory SQLite database (reset on restart).

## Endpoints

- `GET /health` — health check
- `POST /books` — create (`{title, author, year?, isbn?}`; `title` and `author` required)
- `GET /books` — list; optional `?author=` filter
- `GET /books/{id}` — fetch one
- `PUT /books/{id}` — update
- `DELETE /books/{id}` — delete

## Test

```
cargo test
```
