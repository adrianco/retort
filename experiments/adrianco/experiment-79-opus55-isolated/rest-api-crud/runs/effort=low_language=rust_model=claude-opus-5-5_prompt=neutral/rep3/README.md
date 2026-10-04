# Books API

A small REST service for managing a book collection, written in Rust with
[axum](https://github.com/tokio-rs/axum) and SQLite (via `rusqlite`, bundled — no
system SQLite needed).

## Setup and run

Requires a recent stable Rust toolchain (and a C compiler, for the bundled SQLite).

```bash
cargo run --release
```

The server listens on `127.0.0.1:3000` and stores data in `books.db` by default.
Both are configurable:

| Variable        | Default          | Purpose                                        |
|-----------------|------------------|------------------------------------------------|
| `BIND_ADDR`     | `127.0.0.1:3000` | Address and port to listen on                  |
| `DATABASE_PATH` | `books.db`       | SQLite file (`:memory:` for a throwaway store) |

## Tests

```bash
cargo test
```

Integration tests in `tests/api.rs` drive the router in-process against an
in-memory database.

## API

A book looks like:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593" }
```

`title` and `author` are required and must be non-blank; `year` (integer) and
`isbn` (string) are optional and returned as `null` when absent.

| Method | Path          | Description                                  | Success | Errors   |
|--------|---------------|----------------------------------------------|---------|----------|
| GET    | `/health`     | Health check, returns `{"status":"ok"}`      | 200     |          |
| POST   | `/books`      | Create a book                                | 201     | 400      |
| GET    | `/books`      | List books; `?author=` filters by exact author (case-insensitive) | 200 | |
| GET    | `/books/{id}` | Fetch one book                               | 200     | 400, 404 |
| PUT    | `/books/{id}` | Replace a book (full body, same rules as POST) | 200   | 400, 404 |
| DELETE | `/books/{id}` | Delete a book                                | 204     | 400, 404 |

Errors are JSON: `{"error": "..."}`. Validation failures (400) also include a
`details` array, e.g. `["title is required"]`. Malformed JSON and non-integer
ids also return 400.

### Example

```bash
curl -i -X POST localhost:3000/books -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl 'localhost:3000/books?author=Frank%20Herbert'
curl -X PUT localhost:3000/books/1 -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -i -X DELETE localhost:3000/books/1
```
