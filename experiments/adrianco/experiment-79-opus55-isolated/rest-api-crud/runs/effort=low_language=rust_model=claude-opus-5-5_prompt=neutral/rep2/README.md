# Books API

A REST API for managing a book collection, written in Rust with
[axum](https://github.com/tokio-rs/axum) and SQLite (via `rusqlite`).

## Setup

Requires a Rust toolchain (1.75+) and a C compiler; SQLite itself is compiled
in, so nothing else needs installing.

```bash
cargo build --release
```

## Run

```bash
cargo run --release
```

The server listens on `http://0.0.0.0:3000` and stores data in `books.db` in
the current directory. Both are configurable:

| Variable        | Default    | Meaning                   |
|-----------------|------------|---------------------------|
| `PORT`          | `3000`     | TCP port to listen on     |
| `DATABASE_PATH` | `books.db` | SQLite database file path |

## Test

```bash
cargo test
```

Integration tests in `tests/api.rs` drive the router against an in-memory
database.

## API

A book looks like:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719" }
```

`title` and `author` are required non-blank strings; `year` (integer) and
`isbn` (string) are optional and returned as `null` when absent.

| Method | Path          | Description                          | Success |
|--------|---------------|--------------------------------------|---------|
| GET    | `/health`     | Health check                         | 200     |
| POST   | `/books`      | Create a book                        | 201     |
| GET    | `/books`      | List books; `?author=` filters       | 200     |
| GET    | `/books/{id}` | Get one book                         | 200     |
| PUT    | `/books/{id}` | Replace a book (all fields)          | 200     |
| DELETE | `/books/{id}` | Delete a book                        | 204     |

The `author` filter is an exact, case-insensitive match. `PUT` is a full
replacement: optional fields left out are cleared.

Errors are JSON with an `error` field:

| Status | When                                                       |
|--------|------------------------------------------------------------|
| 400    | Body is not valid JSON or a field has the wrong type       |
| 404    | No book with that ID                                       |
| 422    | Missing/blank `title` or `author` (see `details` array)    |

### Examples

```bash
curl -X POST localhost:3000/books -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'localhost:3000/books?author=Frank%20Herbert'
curl localhost:3000/books/1
curl -X PUT localhost:3000/books/1 -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -X DELETE localhost:3000/books/1
```
