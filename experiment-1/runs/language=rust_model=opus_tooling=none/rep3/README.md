# Books API

A small REST API for managing a book collection, written in Rust with axum and SQLite (rusqlite, bundled).

## Requirements
- Rust (1.75+)

## Run
```
cargo run --release
```
Server listens on `http://0.0.0.0:3000`. Data is persisted to `books.db` in the working directory.

## Test
```
cargo test
```

## Endpoints
- `GET /health` — health check
- `POST /books` — create a book. Body: `{"title": "...", "author": "...", "year": 2020, "isbn": "..."}` (`title` and `author` required)
- `GET /books` — list all books. Optional filter: `?author=Name`
- `GET /books/{id}` — fetch one book
- `PUT /books/{id}` — update a book (same body schema as POST)
- `DELETE /books/{id}` — delete a book

### Responses
- `200 OK` / `201 Created` / `204 No Content` on success
- `400 Bad Request` when `title` or `author` is missing
- `404 Not Found` when the book id does not exist

## Example
```
curl -X POST localhost:3000/books -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

curl localhost:3000/books
curl 'localhost:3000/books?author=Frank%20Herbert'
```
