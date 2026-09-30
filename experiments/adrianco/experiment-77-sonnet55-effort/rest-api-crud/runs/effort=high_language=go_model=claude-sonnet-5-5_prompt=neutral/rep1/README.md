# Book Collection API

A REST API for managing a book collection, written in Go using only the standard
library `net/http` router and an embedded SQLite database
([modernc.org/sqlite](https://pkg.go.dev/modernc.org/sqlite), pure Go — no cgo needed).

## Requirements

- Go 1.22 or newer

## Run

```sh
go run .
```

Configuration via environment variables:

| Variable  | Default    | Description              |
|-----------|------------|--------------------------|
| `ADDR`    | `:8080`    | Listen address           |
| `DB_PATH` | `books.db` | SQLite database file     |

## Test

```sh
go test ./...
```

## API

A book is `{"id", "title", "author", "year", "isbn"}`. `title` and `author` are
required (non-blank); `year` must not be negative. Errors return
`{"error": "..."}`.

| Method & path       | Description                          | Success |
|---------------------|--------------------------------------|---------|
| `GET /health`       | Health check                         | 200     |
| `POST /books`       | Create a book                        | 201     |
| `GET /books`        | List books (optional `?author=`)     | 200     |
| `GET /books/{id}`   | Get a book                           | 200     |
| `PUT /books/{id}`   | Replace a book                       | 200     |
| `DELETE /books/{id}`| Delete a book                        | 204     |

Other statuses: `400` invalid input or id, `404` unknown book.

### Example

```sh
curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl 'localhost:8080/books?author=Frank%20Herbert'
curl -X PUT localhost:8080/books/1 -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"123"}'
curl -X DELETE localhost:8080/books/1
```
