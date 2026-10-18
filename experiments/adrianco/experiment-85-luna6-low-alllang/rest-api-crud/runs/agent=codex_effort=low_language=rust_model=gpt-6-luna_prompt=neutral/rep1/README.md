# Book API

A small REST API for managing books, built with Rust, Axum, and SQLite.

## Run

Install Rust using [rustup](https://rustup.rs/), then run:

```sh
cargo run
```

The server listens on `127.0.0.1:3000` and creates `books.db` in the current directory. Configure `DATABASE_URL` (for example, `sqlite://books.db`) and `BIND_ADDR` to change these defaults.

## Endpoints

- `GET /health` — returns `"ok"`
- `POST /books` — create a book; JSON fields: `title`, `author`, optional `year`, optional `isbn`
- `GET /books?author=...` — list books, optionally filtered by exact author
- `GET /books/{id}` — get a book
- `PUT /books/{id}` — replace a book (same JSON fields as create)
- `DELETE /books/{id}` — delete a book

Book title and author must be non-empty. Errors are JSON objects with an `error` field.

## Test

```sh
cargo test
```
