# Book Collection API

A small REST service in Go for managing a book collection. It uses the standard
library `net/http` router (Go 1.22+ method/path patterns) and SQLite via the
pure-Go driver `modernc.org/sqlite`, so no C compiler or CGO is needed.

## Setup

Requires Go 1.22 or newer.

```sh
go mod download
go build -o bookapi .
```

## Run

```sh
./bookapi                         # listens on :8080, stores data in ./books.db
ADDR=:9000 DB_PATH=/tmp/b.db ./bookapi
# or: go run .
```

| Env var   | Default    | Meaning               |
|-----------|------------|-----------------------|
| `ADDR`    | `:8080`    | listen address        |
| `DB_PATH` | `books.db` | SQLite database file  |

## Endpoints

| Method | Path          | Description                                   | Success |
|--------|---------------|-----------------------------------------------|---------|
| GET    | `/health`     | Health check (pings the database)             | 200     |
| POST   | `/books`      | Create a book                                 | 201     |
| GET    | `/books`      | List books; `?author=` filters (case-insensitive exact match) | 200 |
| GET    | `/books/{id}` | Get one book                                  | 200     |
| PUT    | `/books/{id}` | Replace a book's fields                       | 200     |
| DELETE | `/books/{id}` | Delete a book                                 | 204     |

Book JSON:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}
```

Validation (on POST and PUT): `title` and `author` are required (non-blank);
`year` must be between 0 and next year; `isbn`, if given, must be 10 or 13 digits
(hyphens allowed, ISBN-10 may end in `X`). Unknown fields are rejected.

Errors are JSON: `{"error": "..."}`. Validation failures return 400 with a
per-field map: `{"error": "validation failed", "fields": {"title": "title is required"}}`.
Missing books return 404; a non-numeric or non-positive id returns 400.

## Examples

```sh
curl -X POST localhost:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'
curl localhost:8080/books?author=Frank%20Herbert
curl -X PUT localhost:8080/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
curl -X DELETE localhost:8080/books/1
curl localhost:8080/health
```

## Tests

```sh
go test ./...
```

Tests run the full HTTP handler stack against a temporary SQLite file and cover
health, the CRUD lifecycle, the author filter, validation, 404/400 handling and
persistence across reopening the database.
