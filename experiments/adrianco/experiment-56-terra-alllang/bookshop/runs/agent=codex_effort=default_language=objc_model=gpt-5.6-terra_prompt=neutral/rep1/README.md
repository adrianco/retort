# Book Collection API

A small Objective-C REST API backed by SQLite. It uses Foundation and BSD sockets, so no third-party web framework is required.

## Run

```sh
make
PORT=8080 BOOKS_DB=books.db ./book-api
```

`PORT` defaults to `8080`; `BOOKS_DB` defaults to `books.db` in the current directory.

## Endpoints

| Method | Endpoint | Result |
| --- | --- | --- |
| GET | `/health` | `{"status":"ok"}` |
| POST | `/books` | Create a book; `title` and `author` are required |
| GET | `/books` | List books; use `?author=Name` to filter |
| GET | `/books/{id}` | Fetch a book |
| PUT | `/books/{id}` | Update supplied fields (title/author remain required after update) |
| DELETE | `/books/{id}` | Delete a book |

Requests and responses are JSON. Successful creates return `201`, deletes return `204`, malformed or invalid input returns `400`, and missing books return `404`.

Example:

```sh
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'http://localhost:8080/books?author=Frank%20Herbert'
```

## Tests

```sh
make test
```

The test executable covers creation, required-field validation, author filtering, updating, and deletion.
