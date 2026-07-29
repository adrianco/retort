# Book API

A REST API for managing books, using Go's `net/http` and SQLite.

## Run

Requires Go 1.25 or newer.

```sh
go run .
```

The service listens on `http://localhost:8080` and stores data in `books.db`.

## Endpoints

- `GET /health`
- `POST /books` with JSON such as `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}`
- `GET /books` (optionally `?author=Frank%20Herbert`)
- `GET /books/{id}`
- `PUT /books/{id}` with the same JSON fields as create
- `DELETE /books/{id}`

Title and author are required for create and update. Successful deletion returns `204 No Content`; missing books return `404`.

## Test

```sh
go test ./...
```
