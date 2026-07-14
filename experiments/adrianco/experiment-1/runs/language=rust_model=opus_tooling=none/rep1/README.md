# Books API

A small REST API for managing a book collection, written in Rust with axum and SQLite (via rusqlite, bundled).

## Requirements

- Rust (stable, tested with 1.94)

## Build

```
cargo build
```

## Run

```
cargo run
```

The server listens on `http://0.0.0.0:3000`. Data is stored in an in-memory SQLite database.

## Endpoints

- `GET /health` — health check
- `POST /books` — create book. Body: `{"title","author","year?","isbn?"}`. `title` and `author` are required.
- `GET /books` — list books. Optional `?author=` filter.
- `GET /books/{id}` — fetch one book
- `PUT /books/{id}` — replace book fields (title and author required)
- `DELETE /books/{id}` — delete book

Responses are JSON. Status codes: 200 OK, 201 Created, 204 No Content, 400 Bad Request, 404 Not Found.

## Tests

```
cargo test
```

Integration tests cover: health check, create+get, validation, update+delete round-trip, and author filtering.
