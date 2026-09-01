# Book Collection API

A small REST service for managing a book collection, written in Go using only the
standard library `net/http` router and SQLite (via the pure-Go `modernc.org/sqlite`
driver, so no cgo or system SQLite is needed).

## Requirements

- Go 1.22 or newer

## Setup and run

```sh
go mod tidy        # downloads the SQLite driver
go run .           # listens on :8080, stores data in ./books.db
```

Environment variables:

| Variable   | Default    | Purpose                          |
|------------|------------|----------------------------------|
| `ADDR`     | `:8080`    | Listen address                   |
| `BOOKS_DB` | `books.db` | SQLite file path (`:memory:` ok) |

## Run tests

```sh
go test ./...
```

## Endpoints

| Method | Path                   | Description                                  |
|--------|------------------------|----------------------------------------------|
| GET    | `/health`              | Health check, returns `{"status":"ok"}`      |
| POST   | `/books`               | Create a book (201). `title` and `author` required |
| GET    | `/books`               | List books. Optional `?author=` exact filter |
| GET    | `/books/{id}`          | Get one book (404 if missing)                |
| PUT    | `/books/{id}`          | Replace a book (200, 404 if missing)         |
| DELETE | `/books/{id}`          | Delete a book (204, 404 if missing)          |

Book JSON shape:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}
```

Validation failures and malformed JSON return `400` with `{"error": "..."}`.

## Example

```sh
curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl localhost:8080/books?author=Frank%20Herbert
curl -X PUT localhost:8080/books/1 -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"x"}'
curl -X DELETE localhost:8080/books/1
```
