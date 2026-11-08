# Book collection API

Requires Erlang/OTP 27 or later (with the `json` module) and the `sqlite3` command-line program with SQLite 3.35 or later.

Compile and run from this directory:

```sh
erlc books.erl
erl -noshell -s books start
```

The server listens on port 8080 by default. Set `PORT` to change the port and `BOOKS_DB` to change the SQLite database path (default `books.db`). Stop it with Ctrl-C.

Endpoints return JSON. `POST /books` creates a book, `GET /books` lists books, `GET /books?author=Jane%20Doe` filters by exact author, and `GET`, `PUT`, or `DELETE /books/{id}` operate on a single book. `GET /health` returns the service status. POST and PUT accept a JSON object with nonblank string `title` and `author`; `year` is an optional integer and `isbn` an optional string. PUT replaces the full book; omitted optional fields become null. DELETE returns the deleted book. Errors return a JSON object with an `error` field.

```sh
curl -X POST http://localhost:8080/books -H 'Content-Type: application/json' -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl http://localhost:8080/books
```

Run tests:

```sh
erlc books.erl books_tests.erl
erl -noshell -eval 'case eunit:test(books_tests, [verbose]) of ok -> halt(0); _ -> halt(1) end.'
```
