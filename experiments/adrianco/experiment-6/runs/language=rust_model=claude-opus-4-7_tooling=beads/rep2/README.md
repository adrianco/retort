# books_api

A small REST API for managing a book collection, written in Rust with
[axum](https://docs.rs/axum) and an embedded SQLite database
([rusqlite](https://docs.rs/rusqlite) with the bundled SQLite library — no
system dependencies required).

## Requirements

- Rust toolchain (stable, 1.75+ recommended) — install via [rustup](https://rustup.rs).

## Build & Run

```bash
cargo run --release
```

The server listens on `0.0.0.0:3000` by default and stores data in
`books.db` in the working directory.

Environment variables:

| Variable        | Default     | Description                       |
| --------------- | ----------- | --------------------------------- |
| `PORT`          | `3000`      | TCP port to bind to               |
| `DATABASE_PATH` | `books.db`  | Path to the SQLite database file  |

## Tests

```bash
cargo test
```

The test suite uses an in-memory SQLite database and exercises the routes
end-to-end via `tower::ServiceExt::oneshot` without binding a TCP socket.

## API

All endpoints return JSON. The `Book` resource has shape:

```json
{
  "id": "uuid string",
  "title": "string",
  "author": "string",
  "year": 1999,
  "isbn": "978-..."
}
```

`year` and `isbn` are optional and may be `null`.

### `GET /health`

Returns `200 OK` with `{ "status": "ok" }`.

### `POST /books`

Create a book. Request body:

```json
{ "title": "...", "author": "...", "year": 1999, "isbn": "..." }
```

`title` and `author` are required and must be non-empty. Returns `201 Created`
with the created book, or `400 Bad Request` if validation fails.

### `GET /books`

List all books. Supports a `?author=` query parameter to filter by exact
author match. Returns `200 OK` with a JSON array.

### `GET /books/{id}`

Return a single book by id. Returns `200 OK` or `404 Not Found`.

### `PUT /books/{id}`

Partial update — any field omitted from the request body is left untouched.
Returns `200 OK` with the updated book, `400 Bad Request` if a provided field
is invalid, or `404 Not Found` if no such book exists.

### `DELETE /books/{id}`

Returns `204 No Content` on success, or `404 Not Found` if no such book exists.

## Example

```bash
curl -s -X POST localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"The Pragmatic Programmer","author":"Andy Hunt","year":1999}'

curl -s localhost:3000/books?author=Andy%20Hunt
```
