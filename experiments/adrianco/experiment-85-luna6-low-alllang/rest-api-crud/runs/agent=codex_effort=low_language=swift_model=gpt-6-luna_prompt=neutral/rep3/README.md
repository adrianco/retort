# Book Service

A small REST API written in Swift. It uses Apple’s Network framework for HTTP and SQLite for persistent storage.

## Requirements

- macOS 13 or later
- Swift 6 or later
- SQLite development headers/library available to SwiftPM (included with standard macOS developer tools)

## Build and run

```sh
swift build
swift run
```

The service listens on port `8080` and creates `books.sqlite` in the current directory. Set `PORT` and `DATABASE_PATH` to override these values.

## API

- `GET /health` — health status
- `POST /books` — create (`{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`)
- `GET /books` — list books; optionally filter by exact author with `?author=Frank%20Herbert`
- `GET /books/{id}` — fetch one book
- `PUT /books/{id}` — replace the book fields using the same JSON shape as create
- `DELETE /books/{id}` — delete a book

Title and author are required and cannot be blank. Missing records return 404, invalid input returns 400, successful create returns 201, and delete returns 204.

## Tests

```sh
swift test
```
