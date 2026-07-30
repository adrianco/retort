# Book Collection API

A Go REST API backed by SQLite.

## Run

```sh
go run .
```

The service listens on `http://localhost:8080` and creates `books.db` in the current directory. Set `ADDR` to choose a listen address and `BOOKS_DB` to choose a database path.

## Endpoints

- `GET /health`
- `POST /books` — JSON body: `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`
- `GET /books` and `GET /books?author=Frank%20Herbert`
- `GET /books/{id}`
- `PUT /books/{id}` — accepts the same JSON body as POST
- `DELETE /books/{id}`

`title` and `author` are required. Responses are JSON; successful deletion returns `204 No Content`.

## Test

```sh
go test ./...
```
