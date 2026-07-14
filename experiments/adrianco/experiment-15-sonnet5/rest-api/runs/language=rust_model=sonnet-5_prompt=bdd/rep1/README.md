# Book API

A REST API for managing a book collection, built with [Axum](https://github.com/tokio-rs/axum) and backed by an embedded [SQLite](https://www.sqlite.org/) database (via `rusqlite`, bundled — no system SQLite install required).

## Requirements

- Rust (edition 2021) and Cargo — install via [rustup](https://rustup.rs/)

## Setup & Run

```bash
# Build
cargo build

# Run the server (defaults to 0.0.0.0:3000, sqlite file ./books.db)
cargo run
```

Configuration is via environment variables (both optional):

| Variable        | Default        | Description                                   |
|-----------------|----------------|------------------------------------------------|
| `BOOK_API_ADDR` | `0.0.0.0:3000` | Address/port the server binds to                |
| `BOOK_API_DB`   | `books.db`     | Path to the SQLite file (`:memory:` supported)  |

```bash
BOOK_API_ADDR=127.0.0.1:8080 BOOK_API_DB=/tmp/books.db cargo run
```

## API

| Method | Path                    | Description                                  |
|--------|-------------------------|-----------------------------------------------|
| GET    | `/health`                | Health check                                  |
| POST   | `/books`                 | Create a book                                 |
| GET    | `/books`                 | List all books (optional `?author=` filter)   |
| GET    | `/books/{id}`            | Get a single book by ID                       |
| PUT    | `/books/{id}`            | Update a book                                 |
| DELETE | `/books/{id}`            | Delete a book                                 |

### Book payload (POST / PUT)

```json
{
  "title": "1984",
  "author": "George Orwell",
  "year": 1949,
  "isbn": "978-0451524935"
}
```

`title` and `author` are required and must be non-empty; `year` and `isbn` are optional.

### Example requests

```bash
# Create
curl -X POST http://localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"1984","author":"George Orwell","year":1949,"isbn":"978-0451524935"}'

# List all
curl http://localhost:3000/books

# List by author
curl 'http://localhost:3000/books?author=George%20Orwell'

# Get one
curl http://localhost:3000/books/1

# Update
curl -X PUT http://localhost:3000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"Animal Farm","author":"George Orwell"}'

# Delete
curl -X DELETE http://localhost:3000/books/1

# Health check
curl http://localhost:3000/health
```

### Status codes

- `200 OK` — successful GET/PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — validation failure (missing/blank title or author)
- `404 Not Found` — no book with the given ID
- `500 Internal Server Error` — unexpected database/server error

## Tests

Integration tests spin up the Axum router against an isolated in-memory SQLite database per test (no server process or network needed) and are written in BDD (Given/When/Then) style.

```bash
cargo test
```
