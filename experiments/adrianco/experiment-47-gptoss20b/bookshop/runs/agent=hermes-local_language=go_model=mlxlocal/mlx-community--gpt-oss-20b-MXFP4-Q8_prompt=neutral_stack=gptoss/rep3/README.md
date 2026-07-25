# Book API

A simple REST API for managing a book collection.

## Requirements
- Go 1.22 or newer
- SQLite (bundled via `github.com/mattn/go-sqlite3`)

## Setup
```bash
# download dependencies
go mod download

# run the server
go run .
```
The server listens on `:8080`.

## Endpoints
- `GET /health` – health check
- `POST /books` – create book (JSON body: title, author, year, isbn)
- `GET /books` – list all books (optionally filter with `?author=`)
- `GET /books/{id}` – get a book
- `PUT /books/{id}` – update a book
- `DELETE /books/{id}` – delete a book

## Testing
Run tests with:
```bash
go test ./...
```
All tests should pass.
