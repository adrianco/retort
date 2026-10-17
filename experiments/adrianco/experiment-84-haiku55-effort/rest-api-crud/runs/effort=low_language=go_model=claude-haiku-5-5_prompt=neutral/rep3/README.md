# Book Collection API

A REST API for managing a book collection, written in Go using the standard
library `net/http` router and an embedded SQLite database
([`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite), pure Go, no cgo).

## Requirements

- Go 1.22 or newer (uses `net/http` method and path-wildcard routing)

## Setup

```sh
go mod download
```

## Run

```sh
go run .
```

The server listens on `:8080` and stores data in `books.db` in the working directory.
Both can be changed with environment variables:

| Variable  | Default    | Purpose                    |
|-----------|------------|----------------------------|
| `ADDR`    | `:8080`    | HTTP listen address        |
| `DB_PATH` | `books.db` | Path to the SQLite file    |

Example:

```sh
ADDR=:9000 DB_PATH=/tmp/books.db go run .
```

## Test

```sh
go test ./...
```

## Data model

| Field    | Type    | Required | Notes                                  |
|----------|---------|----------|----------------------------------------|
| `id`     | integer | read-only | Assigned by the server                |
| `title`  | string  | yes      | Non-blank after trimming whitespace    |
| `author` | string  | yes      | Non-blank after trimming whitespace    |
| `year`   | integer | no       | 0–9999; defaults to `0` (unknown)      |
| `isbn`   | string  | no       | Defaults to `""`                       |

## Endpoints

| Method | Path          | Success | Description                                   |
|--------|---------------|---------|-----------------------------------------------|
| POST   | `/books`      | 201     | Create a book                                 |
| GET    | `/books`      | 200     | List books; optional `?author=` filter        |
| GET    | `/books/{id}` | 200     | Get one book                                  |
| PUT    | `/books/{id}` | 200     | Replace a book's fields (full update)         |
| DELETE | `/books/{id}` | 204     | Delete a book                                 |
| GET    | `/health`     | 200     | Liveness and database check                   |

The `author` filter matches case-insensitively on the full author string.

### Examples

```sh
# Create
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Left Hand of Darkness","author":"Ursula K. Le Guin","year":1969,"isbn":"978-0441478125"}'

# List, filtered by author
curl 'localhost:8080/books?author=Ursula%20K.%20Le%20Guin'

# Get, update, delete
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Left Hand of Darkness","author":"Ursula K. Le Guin","year":1969,"isbn":""}'
curl -X DELETE localhost:8080/books/1

# Health
curl localhost:8080/health
```

## Errors

Error responses have the shape `{"error": "<message>"}`.

| Status | Cause                                                                 |
|--------|-----------------------------------------------------------------------|
| 400    | Malformed JSON, unknown fields, validation failure, or non-numeric/non-positive ID |
| 404    | No book with the given ID                                             |
| 500    | Unexpected server or database error (details are logged, not returned) |
| 503    | `/health` when the database cannot be reached                         |

Request bodies are limited to 1 MiB.

## Project layout

- `main.go` — configuration, server startup, graceful shutdown
- `server.go` — HTTP handlers, request decoding, validation
- `store.go` — SQLite persistence
- `server_test.go` — integration tests that exercise the HTTP API against a temporary database
