# books-api

A small REST API for managing a book collection, written in Rust with
[axum](https://docs.rs/axum) and SQLite (via `rusqlite`, bundled).

## Requirements

- Rust (stable) with `cargo`

## Run

```bash
cargo run
```

The service listens on `http://0.0.0.0:3000` and writes data to `books.db`
in the working directory.

## Test

```bash
cargo test
```

Tests use an in-memory SQLite database, so they don't touch `books.db`.

## Endpoints

| Method | Path          | Description                                   |
| ------ | ------------- | --------------------------------------------- |
| GET    | `/health`     | Health check — returns `{"status":"ok"}`      |
| POST   | `/books`      | Create a book                                 |
| GET    | `/books`      | List books (optional `?author=` filter)       |
| GET    | `/books/{id}` | Get one book                                  |
| PUT    | `/books/{id}` | Update a book                                 |
| DELETE | `/books/{id}` | Delete a book                                 |

### Book shape

```json
{
  "id": "uuid",
  "title": "string (required)",
  "author": "string (required)",
  "year": 1965,
  "isbn": "optional string"
}
```

### Status codes

- `201 Created` — book created
- `200 OK` — successful read/update/list
- `204 No Content` — delete succeeded
- `400 Bad Request` — missing `title` or `author`
- `404 Not Found` — unknown id

### Examples

```bash
curl -X POST localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

curl 'localhost:3000/books?author=Frank%20Herbert'
```
