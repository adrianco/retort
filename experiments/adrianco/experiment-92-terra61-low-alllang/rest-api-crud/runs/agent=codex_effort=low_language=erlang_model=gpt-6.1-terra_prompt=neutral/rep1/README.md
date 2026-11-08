# Book collection API

Requires Erlang/OTP 27 or later (including EUnit for tests). It uses the OTP JSON module and DETS embedded database; no external packages are needed.

Compile and run from this directory:

```sh
erlc books_store.erl books.erl
erl -noshell -eval 'books:start(), receive stop -> ok end.'
```

The service listens on port 8080 by default. Set `PORT` to change it and `BOOKS_DB` to change the database file (default `books.dets`). Stop the Erlang VM to shut down the service.

```sh
curl -X POST http://localhost:8080/books -H 'Content-Type: application/json' -d '{"title":"Example","author":"Ada","year":2020,"isbn":"123"}'
curl 'http://localhost:8080/books?author=Ada'
curl http://localhost:8080/books/1
curl -X PUT http://localhost:8080/books/1 -H 'Content-Type: application/json' -d '{"title":"Revised","author":"Ada"}'
curl -X DELETE http://localhost:8080/books/1
curl http://localhost:8080/health
```

`title` and `author` must be nonempty strings; `year`, if supplied, must be an integer, and `isbn` a string. Optional fields default to `null`. PUT replaces the book's fields and requires title and author. Author filtering matches the complete author value exactly and is case sensitive. IDs are assigned by the service and persist across restarts. Deletion returns a JSON confirmation.

Run tests:

```sh
erlc books_store.erl books.erl books_tests.erl
erl -noshell -eval 'case eunit:test(books_tests, [verbose]) of ok -> halt(0); _ -> halt(1) end.'
```
