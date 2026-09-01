# book-api

A small REST API for managing a book collection, written in Rust with
[Axum](https://github.com/tokio-rs/axum) and SQLite (via `rusqlite` with the
bundled SQLite engine, so no system SQLite install is needed).

## Setup

Requires a Rust toolchain (1.75+). Build with:

```sh
cargo build --release
```

## Run

```sh
cargo run --release
```

The server listens on `http://0.0.0.0:3000` and stores data in `books.db` in the
current directory. Override with environment variables:

| Variable        | Default    | Purpose                              |
|-----------------|------------|--------------------------------------|
| `PORT`          | `3000`     | TCP port to listen on                |
| `DATABASE_PATH` | `books.db` | SQLite file path (`:memory:` for RAM)|

## Endpoints

| Method | Path              | Description                                  |
|--------|-------------------|----------------------------------------------|
| GET    | `/health`         | Health check, returns `{"status":"ok"}`      |
| POST   | `/books`          | Create a book, returns 201 with the book     |
| GET    | `/books`          | List books; `?author=Name` filters by author |
| GET    | `/books/{id}`     | Fetch one book (404 if missing)              |
| PUT    | `/books/{id}`     | Replace a book's fields (404 if missing)     |
| DELETE | `/books/{id}`     | Delete a book, returns 204 (404 if missing)  |

Book JSON shape:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593" }
```

`title` and `author` are required and must be non-blank; `year` (0–9999) and
`isbn` (10 or 13 digits) are optional. Validation failures return 400 with
`{"error": "..."}`.

Example:

```sh
curl -X POST localhost:3000/books -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl 'localhost:3000/books?author=Frank%20Herbert'
```

## Tests

```sh
cargo test
```

Integration tests in `tests/api.rs` exercise every endpoint against an
in-memory SQLite database.
