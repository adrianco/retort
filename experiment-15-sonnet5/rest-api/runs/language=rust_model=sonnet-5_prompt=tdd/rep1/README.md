# Book API

A REST API for managing a book collection, built with Rust, [axum](https://github.com/tokio-rs/axum), and SQLite ([rusqlite](https://github.com/rusqlite/rusqlite)).

## Requirements

- Rust (edition 2021, stable toolchain)

## Setup & Run

```bash
cargo build
cargo run
```

The server listens on `http://0.0.0.0:3000` and stores data in a SQLite file named `books.db` in the working directory (created automatically on first run).

## Run tests

```bash
cargo test
```

## API

### `GET /health`

Health check.

```
200 OK
{"status": "ok"}
```

### `POST /books`

Create a book. `title` and `author` are required (non-empty).

Request body:
```json
{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}
```

- `201 Created` with the created book (including its `id`)
- `400 Bad Request` if `title` or `author` is missing/empty

### `GET /books`

List all books. Optional `?author=` query parameter filters by author (case-insensitive substring match).

- `200 OK` with a JSON array of books

### `GET /books/{id}`

Get a single book by ID.

- `200 OK` with the book
- `404 Not Found` if no book with that ID exists

### `PUT /books/{id}`

Update a book (full replacement). `title` and `author` are required (non-empty).

Request body: same shape as `POST /books`.

- `200 OK` with the updated book
- `400 Bad Request` if `title` or `author` is missing/empty
- `404 Not Found` if no book with that ID exists

### `DELETE /books/{id}`

Delete a book.

- `204 No Content` on success
- `404 Not Found` if no book with that ID exists

## Project layout

- `src/main.rs` — binary entry point, opens the SQLite database and starts the server
- `src/lib.rs` — builds the axum `Router`
- `src/db.rs` — SQLite schema and queries
- `src/handlers.rs` — HTTP handlers
- `src/models.rs` — `Book` and input types
- `tests/` — integration tests (run against an in-memory SQLite database)
