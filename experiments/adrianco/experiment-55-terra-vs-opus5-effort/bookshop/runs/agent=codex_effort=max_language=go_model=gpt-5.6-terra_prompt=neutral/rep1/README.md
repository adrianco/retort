# Book Collection API

A small REST API for a SQLite-backed book collection, implemented in Go's standard HTTP library.

## Requirements

- Go 1.22 or newer

## Run

From this directory:

```sh
go run .
```

The server listens on `http://localhost:8080` and creates `books.db` in the current directory. Configure it with:

```sh
PORT=3000 BOOKS_DB_PATH=/path/to/books.db go run .
```

## API

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Health check; returns `{"status":"ok"}` |
| `POST` | `/books` | Create a book |
| `GET` | `/books` | List all books |
| `GET` | `/books?author=Name` | List books by an exact author match |
| `GET` | `/books/{id}` | Get one book |
| `PUT` | `/books/{id}` | Replace one book |
| `DELETE` | `/books/{id}` | Delete one book |

Create and update requests use this JSON shape. `title` and `author` are required; `year` must not be negative.

```json
{
  "title": "The Left Hand of Darkness",
  "author": "Ursula K. Le Guin",
  "year": 1969,
  "isbn": "9780441478125"
}
```

For example:

```sh
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Kindred","author":"Octavia E. Butler","year":1979,"isbn":"9780807083697"}'

curl http://localhost:8080/books?author=Octavia%20E.%20Butler
```

Successful responses are JSON (`201` for create, `200` for reads/updates, and `204` for delete). Invalid request bodies return `400`, and missing books return `404`.

## Test

```sh
go test ./...
```
