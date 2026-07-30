# Book Collection API

A REST API for storing a book collection. It uses Go's standard HTTP server and SQLite for persistent storage.

## Requirements

- Go 1.26 or later

## Run

```sh
go mod download
go run .
```

The server listens on `http://localhost:8080` and creates `books.db` in the working directory. Set `BOOKS_DB` to select another SQLite database file and `ADDR` to change the listen address.

```sh
BOOKS_DB=/tmp/my-books.db ADDR=:3000 go run .
```

## API

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/health` | Health check |
| `POST` | `/books` | Create a book |
| `GET` | `/books` | List books; optional exact `?author=` filter |
| `GET` | `/books/{id}` | Retrieve a book |
| `PUT` | `/books/{id}` | Replace a book |
| `DELETE` | `/books/{id}` | Delete a book |

Create and update requests accept this JSON shape. `title` and `author` must be non-empty strings.

```json
{
  "title": "The Left Hand of Darkness",
  "author": "Ursula K. Le Guin",
  "year": 1969,
  "isbn": "978-0-441-47812-5"
}
```

For example:

```sh
curl -i -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Kindred","author":"Octavia E. Butler","year":1979,"isbn":"978-0807083697"}'
curl http://localhost:8080/books?author=Octavia%20E.%20Butler
```

## Test

```sh
go test ./...
```
