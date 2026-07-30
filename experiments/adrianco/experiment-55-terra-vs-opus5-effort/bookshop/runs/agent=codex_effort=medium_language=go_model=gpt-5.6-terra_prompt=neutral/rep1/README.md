# Book Collection API

Small REST service for a SQLite-backed book collection. It uses Go's standard HTTP server and a pure-Go SQLite driver.

## Run

Requires Go 1.22 or newer.

```sh
go run .
```

The service listens on `http://localhost:8080` and stores data in `books.db`. Set `PORT` to use another port, or `BOOKS_DB` to set the SQLite database path/DSN.

## Endpoints

- `GET /health`
- `POST /books`
- `GET /books?author=Name`
- `GET /books/{id}`
- `PUT /books/{id}`
- `DELETE /books/{id}`

Create or replace a book with JSON such as:

```json
{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}
```

`title` and `author` are required. JSON responses include an `error` field for client errors.

## Test

```sh
go test ./...
```
