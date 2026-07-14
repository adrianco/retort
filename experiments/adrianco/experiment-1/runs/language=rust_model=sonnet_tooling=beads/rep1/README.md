# Book API

A REST API for managing a book collection, built with Rust, Axum, and SQLite.

## Setup

**Prerequisites:** Rust toolchain (install via [rustup](https://rustup.rs/))

```bash
cargo build --release
```

## Run

```bash
cargo run
```

The server starts on `http://0.0.0.0:3000` and creates a `books.db` SQLite file in the current directory.

## Endpoints

### Health check
```
GET /health
```

### Create a book
```
POST /books
Content-Type: application/json

{ "title": "Rust Programming", "author": "Steve Klabnik", "year": 2022, "isbn": "978-1-7185-0044-0" }
```
- `title` and `author` are required. Returns `201 Created` with the new book, or `400 Bad Request` on validation failure.

### List all books
```
GET /books
GET /books?author=Steve%20Klabnik
```
Supports optional `?author=` query parameter for filtering.

### Get a book
```
GET /books/:id
```
Returns `404 Not Found` if the ID does not exist.

### Update a book
```
PUT /books/:id
Content-Type: application/json

{ "title": "New Title" }
```
All fields are optional; only provided fields are updated.

### Delete a book
```
DELETE /books/:id
```
Returns `204 No Content` on success, `404 Not Found` if the ID does not exist.

## Tests

```bash
cargo test
```

Runs 7 integration tests covering the health check, CRUD operations, author filtering, validation, and error cases.
