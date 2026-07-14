# Book API

A REST API service for managing a book collection, built with Rust, Axum, and SQLite.

## Requirements

- Rust 1.70+ (install via [rustup](https://rustup.rs))

## Setup & Run

```bash
# Build the project
cargo build --release

# Run the server (listens on http://0.0.0.0:3000)
cargo run --release
```

The server stores data in `books.db` (SQLite file) in the current directory, created automatically on first run.

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

{
  "title": "The Rust Programming Language",
  "author": "Steve Klabnik",
  "year": 2019,
  "isbn": "978-1718500440"
}
```

- `title` and `author` are **required**
- `year` and `isbn` are optional

Response: `201 Created`

### List All Books

```
GET /books
GET /books?author=Klabnik     (filter by author substring)
```

Response: `200 OK` — JSON array of books

### Get a Single Book

```
GET /books/{id}
```

Response: `200 OK` or `404 Not Found`

### Update a Book

```
PUT /books/{id}
Content-Type: application/json

{
  "title": "Updated Title"
}
```

All fields are optional; only provided fields are updated.

Response: `200 OK` or `404 Not Found`

### Delete a Book

```
DELETE /books/{id}
```

Response: `200 OK` or `404 Not Found`

## Example Usage

```bash
# Create a book
curl -s -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Rust in Action","author":"Tim McNamara","year":2021}' | jq

# List all books
curl -s http://localhost:3000/books | jq

# Filter by author
curl -s "http://localhost:3000/books?author=Tim" | jq

# Get single book (replace ID)
curl -s http://localhost:3000/books/<id> | jq

# Update a book
curl -s -X PUT http://localhost:3000/books/<id> \
  -H 'Content-Type: application/json' \
  -d '{"year":2022}' | jq

# Delete a book
curl -s -X DELETE http://localhost:3000/books/<id> | jq
```
