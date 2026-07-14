# Book API REST Service

A simple REST API service for managing a book collection, built with Rust and Actix-web.

## Features

- Create books (POST /books)
- List all books (GET /books)
- Get a single book by ID (GET /books/{id})
- Update a book (PUT /books/{id})
- Delete a book (DELETE /books/{id})
- Health check endpoint (GET /health)

## Requirements

- Rust 1.70 or later
- SQLite (bundled via `rusqlite`)

## Building

```bash
cargo build --release
```

## Running

```bash
cargo run --release
```

The server will start on `http://127.0.0.1:8080`.

## API Endpoints

### Health Check

```
GET /health
```

Response:
```json
{"status": "healthy"}
```

### Create Book

```
POST /books
Content-Type: application/json

{
  "title": "Book Title",
  "author": "Author Name",
  "year": 2024,
  "isbn": "1234567890"
}
```

Response: `201 Created` with the created book

### List Books

```
GET /books
```

Optional query parameter:
- `?author=Name` - Filter by author

Response: `200 OK` with array of books

### Get Book by ID

```
GET /books/{id}
```

Response: `200 OK` with book or `404 Not Found`

### Update Book

```
PUT /books/{id}
Content-Type: application/json

{
  "title": "Updated Title",
  "author": "Updated Author",
  "year": 2025,
  "isbn": "0987654321"
}
```

All fields are optional. Response: `200 OK` with updated book or `404 Not Found`

### Delete Book

```
DELETE /books/{id}
```

Response: `204 No Content` or `404 Not Found`

## Database

The API uses SQLite as its database. The database file is named `books.db` by default.

Set the `DATABASE_URL` environment variable to use a different database location.

## Example Usage

```bash
# Create a book
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Rust Programming Language","author":"Steve Klabnik","year":2018,"isbn":"9781593278281"}'

# List all books
curl http://localhost:8080/books

# Get a book by ID
curl http://localhost:8080/books/1

# Update a book
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Rust Programming Language - 2nd Edition"}'

# Delete a book
curl -X DELETE http://localhost:8080/books/1

# Health check
curl http://localhost:8080/health
```
