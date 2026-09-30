# Book Collection API

A REST API for managing a book collection, written in Go using the standard
library `net/http` router and SQLite (via the pure-Go `modernc.org/sqlite`
driver, so no CGO is needed).

## Setup and run

Requires Go 1.22 or newer.

```sh
go build -o bookapi .
./bookapi            # listens on :8080, stores data in ./books.db
```

Configuration via environment variables:

| Variable  | Default    | Description                    |
|-----------|------------|--------------------------------|
| `ADDR`    | `:8080`    | Address to listen on           |
| `DB_PATH` | `books.db` | Path to the SQLite database    |

## Tests

```sh
go test ./...
```

## Endpoints

| Method | Path          | Description                                   |
|--------|---------------|-----------------------------------------------|
| GET    | `/health`     | Health check (`{"status":"ok"}`)              |
| POST   | `/books`      | Create a book (201, `Location` header)        |
| GET    | `/books`      | List books; optional `?author=` exact filter  |
| GET    | `/books/{id}` | Get one book                                  |
| PUT    | `/books/{id}` | Replace a book                                |
| DELETE | `/books/{id}` | Delete a book (204)                           |

A book is `{"id": 1, "title": "...", "author": "...", "year": 1965, "isbn": "..."}`.
`title` and `author` are required (non-blank); `year` must not be negative;
`year` and `isbn` are optional. Errors are returned as `{"error": "message"}`
with status 400 (invalid input or id), 404 (not found) or 500.

## Example

```sh
curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl 'localhost:8080/books?author=Frank%20Herbert'
curl -X PUT localhost:8080/books/1 -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
curl -X DELETE localhost:8080/books/1
```
