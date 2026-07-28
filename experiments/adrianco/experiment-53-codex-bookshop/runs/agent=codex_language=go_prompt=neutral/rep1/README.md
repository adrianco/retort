# Books API

A REST API for managing a SQLite-backed book collection.

## Run

```sh
go run .
```

The server listens on `:8080`. Set `ADDR` to change the address and `BOOKS_DB` to change the SQLite database path.

## API

- `POST /books` with JSON `{ "title": "...", "author": "...", "year": 2024, "isbn": "..." }`
- `GET /books` (optionally `?author=...`)
- `GET`, `PUT`, and `DELETE /books/{id}`
- `GET /health`

Run tests with:

```sh
go test ./...
```
