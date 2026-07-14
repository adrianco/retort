# Book Collection API

A small REST API for managing a book collection, written in **Rust** using
[axum](https://github.com/tokio-rs/axum) for HTTP routing and
[rusqlite](https://github.com/rusqlite/rusqlite) (bundled SQLite) for storage.

The SQLite engine is compiled in via the `bundled` feature, so **no external
database installation is required**.

## Requirements

- Rust toolchain (stable, 2021 edition) — install via [rustup](https://rustup.rs).
- A C compiler (needed to build the bundled SQLite); standard on macOS/Linux.

## Setup & Run

```bash
# Build
cargo build --release

# Run (creates ./books.db on first start)
cargo run --release
```

The server listens on `http://127.0.0.1:3000` by default.

### Configuration (environment variables)

| Variable        | Default           | Description                          |
| --------------- | ----------------- | ------------------------------------ |
| `BIND_ADDR`     | `127.0.0.1:3000`  | Address/port the server binds to.    |
| `DATABASE_PATH` | `books.db`        | SQLite file path (`:memory:` for RAM)|

## API

All request and response bodies are JSON.

| Method | Path           | Description                              | Success |
| ------ | -------------- | ---------------------------------------- | ------- |
| GET    | `/health`      | Health check.                            | 200     |
| POST   | `/books`       | Create a book.                           | 201     |
| GET    | `/books`       | List books. Optional `?author=` filter.  | 200     |
| GET    | `/books/{id}`  | Get one book.                            | 200     |
| PUT    | `/books/{id}`  | Replace a book.                          | 200     |
| DELETE | `/books/{id}`  | Delete a book.                           | 204     |

### Book fields

- `title` *(string, required)*
- `author` *(string, required)*
- `year` *(integer, optional)*
- `isbn` *(string, optional)*

`title` and `author` are validated to be present and non-empty (whitespace-only
values are rejected with `400 Bad Request`). Missing resources return
`404 Not Found`. Errors are returned as `{ "error": "<message>" }`.

### Examples

```bash
# Create
curl -X POST http://127.0.0.1:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"The Rust Programming Language","author":"Steve Klabnik","year":2018,"isbn":"9781593278281"}'

# List (all)
curl http://127.0.0.1:3000/books

# List filtered by author
curl 'http://127.0.0.1:3000/books?author=Steve%20Klabnik'

# Get one
curl http://127.0.0.1:3000/books/1

# Update
curl -X PUT http://127.0.0.1:3000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"The Rust Programming Language, 2nd Edition","author":"Steve Klabnik","year":2022}'

# Delete
curl -X DELETE http://127.0.0.1:3000/books/1

# Health
curl http://127.0.0.1:3000/health
```

## Tests

Integration tests drive the router in-process against an in-memory database:

```bash
cargo test
```

There are 6 tests covering the health check, create/get, validation,
author filtering, update/delete, and the 404 path.

## Project layout

```
src/lib.rs     # Router, handlers, DB access, validation
src/main.rs    # Binary entry point (binds the listener)
tests/api.rs   # Integration tests
```
