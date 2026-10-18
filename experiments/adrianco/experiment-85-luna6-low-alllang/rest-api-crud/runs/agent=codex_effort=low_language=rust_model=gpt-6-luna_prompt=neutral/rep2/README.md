# Book API

A small Rust REST API for managing books. It uses Axum for HTTP routing and SQLite for persistent storage in `books.db` in the working directory.

## Run

Install Rust and Cargo, then from this directory:

```sh
cargo run
```

The service listens on `http://localhost:3000`.

## Endpoints

- `GET /health` — health status
- `POST /books` — create a book (`title` and `author` are required; `year` and `isbn` are optional)
- `GET /books?author=...` — list books, optionally filtering by exact author
- `GET /books/{id}` — fetch one book
- `PUT /books/{id}` — replace a book's fields
- `DELETE /books/{id}` — delete a book

Book requests and responses use JSON. Missing records return `404`; invalid required fields return `400`.

## Tests

```sh
cargo test
```
