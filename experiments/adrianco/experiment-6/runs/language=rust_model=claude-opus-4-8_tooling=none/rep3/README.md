# Book API

A small REST API for managing a book collection, written in Rust with
[axum](https://github.com/tokio-rs/axum) and backed by SQLite (via
[`rusqlite`](https://github.com/rusqlite/rusqlite) with the bundled SQLite,
so no system SQLite install is required).

## Requirements

- Rust (stable, 2021 edition) and Cargo
- A C compiler (needed once to build the bundled SQLite); standard on macOS
  (Xcode command line tools) and Linux (`build-essential`).

## Run

```bash
cargo run
```

The server listens on `http://127.0.0.1:3000` and stores data in `books.db`
in the working directory. Both are configurable via environment variables:

| Variable        | Default          | Description                      |
| --------------- | ---------------- | -------------------------------- |
| `BIND_ADDR`     | `127.0.0.1:3000` | Address/port to bind             |
| `DATABASE_PATH` | `books.db`       | SQLite file (`:memory:` for RAM) |

```bash
BIND_ADDR=0.0.0.0:8080 DATABASE_PATH=/tmp/books.db cargo run
```

## Test

```bash
cargo test
```

The integration tests in `tests/api.rs` drive the router end-to-end against an
in-memory database (health check, CRUD, validation, and the author filter).

## API

A `Book` is returned as:

```json
{ "id": 1, "title": "...", "author": "...", "year": 2018, "isbn": "..." }
```

`year` and `isbn` are optional and may be `null`. `title` and `author` are
required (non-empty after trimming); omitting either yields `400 Bad Request`.

| Method   | Path             | Description                       | Success      |
| -------- | ---------------- | --------------------------------- | ------------ |
| `GET`    | `/health`        | Liveness check                    | `200`        |
| `POST`   | `/books`         | Create a book                     | `201`        |
| `GET`    | `/books`         | List books (`?author=` to filter) | `200`        |
| `GET`    | `/books/{id}`    | Fetch one book                    | `200` / `404`|
| `PUT`    | `/books/{id}`    | Replace a book                    | `200` / `404`|
| `DELETE` | `/books/{id}`    | Delete a book                     | `204` / `404`|

Errors are returned as JSON: `{ "error": "message" }`.

### Examples

```bash
# Create
curl -s -X POST http://127.0.0.1:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"The Rust Programming Language","author":"Steve Klabnik","year":2018,"isbn":"9781593278281"}'

# List (optionally filter by author)
curl -s http://127.0.0.1:3000/books
curl -s 'http://127.0.0.1:3000/books?author=Steve%20Klabnik'

# Get one
curl -s http://127.0.0.1:3000/books/1

# Update
curl -s -X PUT http://127.0.0.1:3000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"TRPL, 2nd Ed.","author":"Steve Klabnik","year":2023}'

# Delete
curl -s -X DELETE http://127.0.0.1:3000/books/1 -i

# Health
curl -s http://127.0.0.1:3000/health
```

## Project layout

- `src/lib.rs` — router, handlers, validation, and SQLite access
- `src/main.rs` — binary entry point (config, bind, serve)
- `tests/api.rs` — integration tests
