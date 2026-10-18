# Book API

A small REST API written in Swift 6. It uses Apple's Network framework for HTTP and SQLite for persistent storage.

## Requirements

- macOS 13 or later with Xcode command line tools
- Swift 6.0 or later
- SQLite development headers and library

## Run

From the repository directory:

```sh
swift run
```

The server listens on port `8080` and creates `books.sqlite` in the current directory. Set `PORT` or `BOOKS_DB` to change these values:

```sh
PORT=9090 BOOKS_DB=/path/to/books.sqlite swift run
```

## Endpoints

- `GET /health` returns `{"status":"ok"}`
- `POST /books` with JSON `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}` creates a book (`201`)
- `GET /books` lists books, with optional `?author=Frank%20Herbert` filter
- `GET /books/{id}` returns a book (`404` if absent)
- `PUT /books/{id}` updates a book with the same JSON fields
- `DELETE /books/{id}` deletes a book (`204` on success)

Title and author are required and must not be blank. Invalid JSON or input returns `400`. Responses use JSON, except successful deletes, which have no body.

## Tests

```sh
swift test
```
