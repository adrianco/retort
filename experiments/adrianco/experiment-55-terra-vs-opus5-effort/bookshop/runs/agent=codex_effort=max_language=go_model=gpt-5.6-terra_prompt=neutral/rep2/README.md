# Book Collection API

A small REST API for managing a SQLite-backed book collection. It uses Go's
standard `net/http` package and the pure-Go SQLite driver from `modernc.org/sqlite`.

## Requirements

- Go 1.20 or newer

## Run

Download dependencies and start the server:

```sh
go mod download
go run .
```

The server listens on `:8080` and creates `books.db` in the current directory.
Set `ADDR` to change the listening address or `DATABASE_PATH` to use another
SQLite database file:

```sh
ADDR=:3000 DATABASE_PATH=./data/books.db go run .
```

## API

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/health` | Returns `{"status":"ok"}`. |
| `POST` | `/books` | Creates a book. |
| `GET` | `/books` | Lists all books. Use `?author=Name` to filter by exact author. |
| `GET` | `/books/{id}` | Gets a single book. |
| `PUT` | `/books/{id}` | Replaces a book. |
| `DELETE` | `/books/{id}` | Deletes a book. |

Book request bodies are JSON. `title` and `author` are required; `year` and
`isbn` are optional.

```sh
curl -i -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Kindred","author":"Octavia E. Butler","year":1979,"isbn":"9780807083697"}'

curl http://localhost:8080/books?author=Octavia%20E.%20Butler
```

Responses are JSON. Successful creation returns `201 Created`, deletion returns
`204 No Content`, missing books return `404 Not Found`, and malformed or invalid
book input returns `400 Bad Request`.

## Test

```sh
go test ./...
```
