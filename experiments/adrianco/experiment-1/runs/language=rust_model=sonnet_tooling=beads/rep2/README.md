# Books API

A REST API service for managing a book collection, built with Rust, Axum, and SQLite.

## Requirements

- Rust 1.75+ (2021 edition)
- Cargo

## Setup & Run

```bash
# Clone / enter the project directory, then:
cargo build --release

# Run (defaults: binds 0.0.0.0:3000, database file books.db)
cargo run --release

# Optional environment variables:
DATABASE_URL=my_books.db BIND_ADDR=127.0.0.1:8080 cargo run --release
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/books` | List all books (supports `?author=` filter) |
| POST | `/books` | Create a new book |
| GET | `/books/:id` | Get a single book by ID |
| PUT | `/books/:id` | Update a book |
| DELETE | `/books/:id` | Delete a book |

## Request / Response Examples

### Create a book
```bash
curl -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "The Rust Programming Language", "author": "Steve Klabnik", "year": 2019, "isbn": "978-1-7185-0044-0"}'
```
Response `201 Created`:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "The Rust Programming Language",
  "author": "Steve Klabnik",
  "year": 2019,
  "isbn": "978-1-7185-0044-0"
}
```

### List books (with optional author filter)
```bash
curl http://localhost:3000/books
curl http://localhost:3000/books?author=Steve+Klabnik
```

### Get a book
```bash
curl http://localhost:3000/books/550e8400-e29b-41d4-a716-446655440000
```

### Update a book
```bash
curl -X PUT http://localhost:3000/books/550e8400-e29b-41d4-a716-446655440000 \
  -H 'Content-Type: application/json' \
  -d '{"year": 2022}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:3000/books/550e8400-e29b-41d4-a716-446655440000
```
Response: `204 No Content`

## Validation

- `title` and `author` are required when creating a book (returns `422 Unprocessable Entity` if missing or blank)
- When updating, if `title` or `author` are provided they must not be blank

## Running Tests

```bash
cargo test
```

5 integration tests are included covering:
- Health check endpoint
- Create and retrieve a book
- Author filter on list
- Validation of missing required fields
- Update and delete a book
