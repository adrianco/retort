# Book Collection API

A REST API for managing a book collection, written in Go using only the standard
library `net/http` router plus an embedded SQLite database
([modernc.org/sqlite](https://pkg.go.dev/modernc.org/sqlite), pure Go — no CGO needed).

## Requirements

- Go 1.22 or newer

## Run

```sh
go run .
```

Configuration via environment variables:

| Variable  | Default    | Description                 |
|-----------|------------|-----------------------------|
| `ADDR`    | `:8080`    | Listen address              |
| `DB_PATH` | `books.db` | SQLite database file path   |

## Test

```sh
go test ./...
```

## Endpoints

| Method | Path            | Description                                   | Success |
|--------|-----------------|-----------------------------------------------|---------|
| GET    | `/health`       | Health check (verifies DB connectivity)       | 200     |
| POST   | `/books`        | Create a book                                 | 201     |
| GET    | `/books`        | List books; optional `?author=` filter        | 200     |
| GET    | `/books/{id}`   | Get one book                                  | 200     |
| PUT    | `/books/{id}`   | Replace a book's fields                       | 200     |
| DELETE | `/books/{id}`   | Delete a book                                 | 204     |

Book JSON:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

`title` and `author` are required (non-blank). `year` (0–9999) and `isbn` are optional.
The `author` filter is an exact, case-insensitive match.

### Errors

Errors are JSON: `{"error": "...", "fields": {"title": "is required"}}`.

- `400` malformed JSON or invalid ID
- `404` book not found
- `413` body larger than 1 MiB
- `422` validation failure (`fields` lists the offending fields)

### Example

```sh
curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl localhost:8080/books?author=Frank%20Herbert
curl -X PUT localhost:8080/books/1 -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl -X DELETE localhost:8080/books/1
```
