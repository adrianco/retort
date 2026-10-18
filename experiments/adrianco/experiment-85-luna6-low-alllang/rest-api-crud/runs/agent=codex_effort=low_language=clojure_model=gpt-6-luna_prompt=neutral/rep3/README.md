# Book Collection API

A small Clojure REST API for managing books. Data is stored in SQLite in `books.db` by default.

## Requirements

- Java 11 or newer
- Clojure CLI tools

## Run

```sh
clojure -M:run
```

The service listens on port 3000. Set `PORT` to change the port and `BOOKS_DB` to select a SQLite database file.

## API

- `GET /health` — health status
- `POST /books` — create a book with JSON `title`, `author`, and optional `year`, `isbn`
- `GET /books` — list books; add `?author=Name` to filter by exact author
- `GET /books/{id}` — retrieve one book
- `PUT /books/{id}` — replace a book
- `DELETE /books/{id}` — delete a book

Title and author are required and must be nonblank strings. Invalid input returns 400; missing IDs return 404. Successful creation returns 201, and deletion returns 204.

## Tests

```sh
clojure -M:test
```
