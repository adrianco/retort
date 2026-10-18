# Book Collection API

A REST API for managing a book collection, written in Go using the standard
library `net/http` router and SQLite storage (via the pure-Go `modernc.org/sqlite`
driver, so no C toolchain is needed).

## Requirements

- Go 1.22 or newer

## Setup

```sh
go mod download
```

## Run

```sh
go run ./cmd/bookapi
```

Configuration via environment variables:

| Variable  | Default     | Description               |
|-----------|-------------|---------------------------|
| `ADDR`    | `:8080`     | HTTP listen address       |
| `DB_PATH` | `books.db`  | Path to the SQLite file   |

Example:

```sh
ADDR=:9000 DB_PATH=/tmp/books.db go run ./cmd/bookapi
```

## Test

```sh
go test ./...
```

## Data model

| Field    | Type    | Required | Notes                        |
|----------|---------|----------|------------------------------|
| `id`     | integer | (server) | Assigned on create           |
| `title`  | string  | yes      | Whitespace-trimmed, non-empty|
| `author` | string  | yes      | Whitespace-trimmed, non-empty|
| `year`   | integer | no       | Must be >= 0 (default 0)     |
| `isbn`   | string  | no       | Free text (default "")       |

## Endpoints

| Method   | Path          | Success       | Description                              |
|----------|---------------|---------------|------------------------------------------|
| `POST`   | `/books`      | `201 Created` | Create a book; `Location` header is set  |
| `GET`    | `/books`      | `200 OK`      | List books; `?author=` filters (case-insensitive exact match) |
| `GET`    | `/books/{id}` | `200 OK`      | Get one book                             |
| `PUT`    | `/books/{id}` | `200 OK`      | Replace a book's fields                  |
| `DELETE` | `/books/{id}` | `204 No Content` | Delete a book                         |
| `GET`    | `/health`     | `200 OK`      | Health check (`503` if DB unreachable)   |

Errors return JSON: `{"error": "..."}`. Validation failures return `400` with
`{"error": "validation failed", "fields": {"title": "is required"}}`.
Missing books return `404`. Unknown JSON fields and malformed bodies return `400`.

## Examples

```sh
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

curl 'localhost:8080/books?author=Frank%20Herbert'
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl -X DELETE localhost:8080/books/1
curl localhost:8080/health
```
