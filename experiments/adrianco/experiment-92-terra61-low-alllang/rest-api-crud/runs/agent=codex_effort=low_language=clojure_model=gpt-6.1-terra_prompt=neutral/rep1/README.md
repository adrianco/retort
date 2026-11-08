# Book collection API

A Clojure Ring service using SQLite. Requires Java and the [Clojure CLI](https://clojure.org/guides/install_clojure); dependencies are downloaded on first use.

Run `clojure -M:run`. The service listens on port 3000 by default; set `PORT` to change it. SQLite data is persisted in `books.db` in the working directory; set `BOOKS_DB` to another SQLite file path. The table is created automatically on startup.

Run the tests with `clojure -M:test`.

All responses are JSON. Books contain `id`, `title`, `author`, `year`, and `isbn`. Title and author must be nonblank strings; year is an optional integer and ISBN is an optional string. Missing optional values are stored as null. PUT replaces the whole book, so it also requires title and author and clears omitted optional values.

- `POST /books`: JSON book, returns 201 and the created book with a `Location` header.
- `GET /books`: returns an array ordered by ID. `?author=...` filters by exact author name (URL-encode the value).
- `GET /books/{id}`: returns a book.
- `PUT /books/{id}`: JSON replacement book, returns the updated book.
- `DELETE /books/{id}`: deletes a book and returns `{"deleted":true}`.
- `GET /health`: returns `{"status":"ok"}`.

Invalid JSON or invalid book fields return 400. Unknown books or routes return 404. Errors have an `error` string in the JSON body.

Example:

```sh
curl -X POST http://localhost:3000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'http://localhost:3000/books?author=Frank%20Herbert'
```
