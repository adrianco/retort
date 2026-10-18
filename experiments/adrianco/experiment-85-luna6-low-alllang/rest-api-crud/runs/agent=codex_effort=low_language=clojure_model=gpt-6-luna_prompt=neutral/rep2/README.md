# Book Collection API

A small Clojure REST API backed by SQLite.

## Requirements

Install Java 17+ and the Clojure CLI.

## Run

From this directory, start the service with:

```sh
clojure -M:run
```

The service listens on port 3000. Set `PORT` to change the port and `BOOKS_DB` to change the SQLite file (defaults to `books.sqlite`).

JSON endpoints:

- `GET /health`
- `POST /books` with `title`, `author`, and optional `year` and `isbn`
- `GET /books` with optional `?author=...`
- `GET /books/{id}`
- `PUT /books/{id}` with a full book object
- `DELETE /books/{id}`

## Tests

```sh
clojure -M:test
```
