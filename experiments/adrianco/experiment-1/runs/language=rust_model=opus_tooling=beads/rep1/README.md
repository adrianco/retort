# books-api

A REST API for managing a book collection, built with Rust, [axum](https://github.com/tokio-rs/axum), and SQLite (via `rusqlite`).

## Setup

Requires Rust 1.75+ (stable).

```bash
cargo build
```

## Run

```bash
cargo run
```

The server listens on `0.0.0.0:3000` and stores data in `books.db` in the current directory.

## Test

```bash
cargo test
```

Integration tests use an in-memory SQLite database.

## Endpoints

| Method | Path          | Description                              |
| ------ | ------------- | ---------------------------------------- |
| GET    | `/health`     | Health check, returns `{"status":"ok"}`  |
| POST   | `/books`      | Create a book                            |
| GET    | `/books`      | List books (supports `?author=` filter)  |
| GET    | `/books/{id}` | Get a single book                        |
| PUT    | `/books/{id}` | Update a book                            |
| DELETE | `/books/{id}` | Delete a book                            |

### Book payload

```json
{
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "978-0441013593"
}
```

`title` and `author` are required; `year` and `isbn` are optional.

### Example

```bash
curl -X POST http://localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

curl http://localhost:3000/books?author=Frank%20Herbert
```

### Status codes

- `201 Created` on successful POST
- `200 OK` on successful GET / PUT
- `204 No Content` on successful DELETE
- `400 Bad Request` when `title` or `author` is missing
- `404 Not Found` when the book id doesn't exist
