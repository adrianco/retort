# Book API

A REST API service for managing a book collection, built with Rust, Actix-Web, and SQLite.

## Endpoints

- `POST /books` — Create a new book
- `GET /books` — List all books (supports `?author=` filter)
- `GET /books/{id}` — Get a single book by ID
- `PUT /books/{id}` — Update a book
- `DELETE /books/{id}` — Delete a book
- `GET /health` — Health check

## Setup

Requires Rust 1.70+ and Cargo.

```bash
cargo build
```

## Running

```bash
cargo run
```

The server starts on `http://0.0.0.0:8080`.

## Testing

```bash
cargo test
```

## Create a book

```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Rust Programming Language","author":"Steve Klabnik","year":2018,"isbn":"978-1-7185-0044-0"}'
```

## List books

```bash
curl http://localhost:8080/books
```

### Filter by author

```bash
curl "http://localhost:8080/books?author=Steve%20Klabnik"
```

## Update a book

```bash
curl -X PUT http://localhost:8080/books/{id} \
  -H "Content-Type: application/json" \
  -d '{"title":"Updated Title"}'
```

## Delete a book

```bash
curl -X DELETE http://localhost:8080/books/{id}
```
