# Book API

A REST API for managing a book collection, built with Rust (Axum + SQLite).

## Requirements

- Rust 1.70+ with Cargo

## Setup & Run

```bash
cargo run
```

The server starts on `http://0.0.0.0:3000` using an in-memory SQLite database.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/books` | Create a book |
| GET | `/books` | List all books (supports `?author=` filter) |
| GET | `/books/:id` | Get a book by ID |
| PUT | `/books/:id` | Update a book |
| DELETE | `/books/:id` | Delete a book |

### Request / Response Examples

**Create a book**
```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Rust Programming Language","author":"Steve Klabnik","year":2019,"isbn":"978-1718500440"}'
```

**List books (optionally filter by author)**
```bash
curl http://localhost:3000/books
curl "http://localhost:3000/books?author=Steve+Klabnik"
```

**Get a book**
```bash
curl http://localhost:3000/books/<id>
```

**Update a book**
```bash
curl -X PUT http://localhost:3000/books/<id> \
  -H "Content-Type: application/json" \
  -d '{"title":"Updated Title"}'
```

**Delete a book**
```bash
curl -X DELETE http://localhost:3000/books/<id>
```

## Validation

`title` and `author` are required on creation. Missing either returns `422 Unprocessable Entity`.

## Tests

```bash
cargo test
```

10 integration tests covering all endpoints, validation, and error cases.
