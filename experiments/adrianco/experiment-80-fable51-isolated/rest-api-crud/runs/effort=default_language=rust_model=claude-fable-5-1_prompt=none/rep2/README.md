# Books API

A REST API for managing a book collection, written in Rust with
[axum](https://github.com/tokio-rs/axum) and SQLite (via
[rusqlite](https://github.com/rusqlite/rusqlite), with SQLite bundled — no
system library needed).

## Setup

Requires a recent stable Rust toolchain (https://rustup.rs) and a C compiler
(used to build the bundled SQLite).

```bash
cargo build --release
```

## Run

```bash
cargo run --release
```

The server listens on `http://127.0.0.1:3000` and stores data in `books.db`
in the current directory. Configure with environment variables:

| Variable        | Default     | Description               |
|-----------------|-------------|---------------------------|
| `HOST`          | `127.0.0.1` | Address to bind           |
| `PORT`          | `3000`      | Port to listen on         |
| `DATABASE_PATH` | `books.db`  | SQLite database file path |

## Test

```bash
cargo test
```

Integration tests live in `tests/api.rs` and run against an in-memory database.

## API

A book looks like:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593" }
```

`title` and `author` are required and must be non-blank; `year` (integer) and
`isbn` (string) are optional and may be `null`.

| Method | Path          | Description                                  | Success |
|--------|---------------|----------------------------------------------|---------|
| GET    | `/health`     | Health check                                 | 200     |
| POST   | `/books`      | Create a book                                | 201     |
| GET    | `/books`      | List books; `?author=` filters by exact name | 200     |
| GET    | `/books/{id}` | Get one book                                 | 200     |
| PUT    | `/books/{id}` | Replace a book (all fields; omitted optional fields become `null`) | 200 |
| DELETE | `/books/{id}` | Delete a book                                | 204     |

Errors are returned as JSON, e.g. `{ "error": "book not found" }`:

- `400` — malformed JSON or a field of the wrong type
- `404` — no book with that ID
- `422` — validation failed; `details` lists the problems, e.g.
  `{ "error": "validation failed", "details": ["title is required"] }`

### Examples

```bash
curl -X POST localhost:3000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl localhost:3000/books
curl 'localhost:3000/books?author=Frank%20Herbert'
curl localhost:3000/books/1
curl -X PUT localhost:3000/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
curl -X DELETE localhost:3000/books/1
```
