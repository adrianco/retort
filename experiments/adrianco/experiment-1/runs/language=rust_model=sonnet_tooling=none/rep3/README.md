# Book API

A REST API service for managing a book collection, built with Rust, Actix-web, and SQLite.

## Prerequisites

- Rust (stable) — install via [rustup](https://rustup.rs)

## Setup and Run

```bash
# Clone/enter the project directory
cd book_api

# Build
cargo build --release

# Run the server (listens on http://127.0.0.1:8080)
cargo run --release
```

The server creates a `books.db` SQLite file in the current directory on first run.

## Running Tests

```bash
cargo test
```

## API Endpoints

### Health Check

```
GET /health
```

Response: `{"status": "ok"}`

---

### Create a Book

```
POST /books
Content-Type: application/json

{
  "title": "The Rust Programming Language",
  "author": "Steve Klabnik",
  "year": 2019,
  "isbn": "978-1718500440"
}
```

- `title` and `author` are required; `year` and `isbn` are optional.
- Returns `201 Created` with the new book object (including generated `id`).

---

### List All Books

```
GET /books
GET /books?author=Klabnik
```

- Optional `?author=` query parameter filters by author (case-insensitive substring match).
- Returns `200 OK` with a JSON array of books.

---

### Get a Book by ID

```
GET /books/{id}
```

- Returns `200 OK` with the book object, or `404 Not Found`.

---

### Update a Book

```
PUT /books/{id}
Content-Type: application/json

{
  "title": "Updated Title",
  "year": 2020
}
```

- All fields are optional; omitted fields keep their existing values.
- Returns `200 OK` with the updated book, or `404 Not Found`.

---

### Delete a Book

```
DELETE /books/{id}
```

- Returns `204 No Content` on success, or `404 Not Found`.

## Example Usage

```bash
# Create a book
curl -s -X POST http://127.0.0.1:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}' | jq

# List all books
curl -s http://127.0.0.1:8080/books | jq

# Filter by author
curl -s 'http://127.0.0.1:8080/books?author=Herbert' | jq

# Get by ID (replace <id> with actual UUID)
curl -s http://127.0.0.1:8080/books/<id> | jq

# Update a book
curl -s -X PUT http://127.0.0.1:8080/books/<id> \
  -H 'Content-Type: application/json' \
  -d '{"year":2021}' | jq

# Delete a book
curl -s -X DELETE http://127.0.0.1:8080/books/<id>
```
