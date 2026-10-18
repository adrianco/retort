# Book API

A small REST API written in Swift. It uses the macOS Network framework for HTTP and SQLite for persistent storage.

## Requirements

- Swift 6.0 or later
- macOS 13 or later (the server uses Apple's Network framework)
- SQLite development headers

## Run

```sh
swift run
```

The server listens on port `8080` and stores data in `books.sqlite` in the current directory. Set `PORT` or `BOOKS_DB` to change these values.

## Endpoints

- `GET /health`
- `POST /books` with JSON: `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`
- `GET /books` and optional `?author=Frank%20Herbert`
- `GET /books/{id}`
- `PUT /books/{id}` with the same JSON fields
- `DELETE /books/{id}`

Title and author are required. Create returns `201`, successful reads and updates return `200`, invalid input returns `400`, and missing books return `404`.

## Test

```sh
swift test
```
