# Book Collection API

A REST API for managing a book collection, built with Rust, Actix-Web, and SQLite.

## Requirements

- Rust 1.70+ (install via [rustup](https://rustup.rs))

## Setup and Run

```bash
# Build
cargo build --release

# Run (starts on http://0.0.0.0:8080)
cargo run --release
```

The SQLite database is stored in `books.db` in the current directory and is created automatically on first run.

## Running Tests

```bash
cargo test
```

## API Endpoints

### Health Check

```
GET /health
```

Response: `200 OK`
```json
{"status": "ok"}
```

### Create a Book

```
POST /books
Content-Type: application/json
```

Body:
```json
{
  "title": "The Rust Programming Language",
  "author": "Steve Klabnik",
  "year": 2019,
  "isbn": "978-1718500440"
}
```

- `title` and `author` are **required**.
- `year` and `isbn` are optional.

Response: `201 Created`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "The Rust Programming Language",
  "author": "Steve Klabnik",
  "year": 2019,
  "isbn": "978-1718500440"
}
```

### List All Books

```
GET /books
GET /books?author=Klabnik
```

- Optional `?author=` query parameter filters by author (case-insensitive substring match).

Response: `200 OK`
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "The Rust Programming Language",
    "author": "Steve Klabnik",
    "year": 2019,
    "isbn": "978-1718500440"
  }
]
```

### Get a Book by ID

```
GET /books/{id}
```

Response: `200 OK` or `404 Not Found`

### Update a Book

```
PUT /books/{id}
Content-Type: application/json
```

Body (all fields optional; omitted fields are unchanged):
```json
{
  "title": "Updated Title",
  "year": 2022
}
```

Response: `200 OK` or `404 Not Found`

### Delete a Book

```
DELETE /books/{id}
```

Response: `204 No Content` or `404 Not Found`
