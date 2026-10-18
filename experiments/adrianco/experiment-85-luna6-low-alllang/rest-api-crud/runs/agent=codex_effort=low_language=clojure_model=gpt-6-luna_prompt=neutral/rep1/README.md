# Book Collection API

A JSON REST API for managing books, implemented in Clojure with Ring/Jetty and SQLite.

## Requirements

- Java 11 or newer
- Clojure CLI tools

## Run

Start the server on port 3000:

```sh
clojure -M:run
```

Set `PORT` to change the listening port and `BOOKS_DB` to choose the SQLite file path. The default database is `books.db` in the working directory.

## API

- `GET /health` — health status
- `POST /books` — create a book (JSON fields: `title`, `author`, optional `year`, `isbn`)
- `GET /books` — list books; optionally filter with `?author=Herbert`
- `GET /books/{id}` — retrieve one book
- `PUT /books/{id}` — replace a book (same JSON fields as creation)
- `DELETE /books/{id}` — remove a book

Titles and authors must be non-empty strings. `year`, when supplied, must be an integer from 0 through 9999. Successful creation returns `201`; successful deletion returns `204`; invalid input returns `400`, and unknown IDs return `404`.

Example:

```sh
curl -i -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
```

## Tests

Run the integration tests with:

```sh
clojure -M:test
```
