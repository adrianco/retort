# Book collection REST API (C)

Small HTTP service using GNU libmicrohttpd and SQLite.

## Dependencies

Install a C compiler, `pkg-config`, SQLite development files, GNU libmicrohttpd development files, and Python 3 (for integration tests). On Debian/Ubuntu: `sudo apt install build-essential pkg-config libsqlite3-dev libmicrohttpd-dev python3`.

## Build and run

```sh
make
./book_server --port 8080 --db books.db
```

The database table is created automatically. Stop the service with Ctrl-C. The `--port` and `--db` arguments are optional.

## API

- `GET /health` returns `{"status":"ok"}`.
- `POST /books` accepts JSON with `title`, `author`, `year`, and `isbn`; title and author are required. Returns `201` and the created record.
- `GET /books` returns all records; `GET /books?author=NAME` filters by exact author.
- `GET /books/{id}` returns one record.
- `PUT /books/{id}` replaces a record using the same JSON fields and required title and author.
- `DELETE /books/{id}` removes a record.

Records contain `id`, `title`, `author`, `year`, and `isbn`. Missing year defaults to 0 and missing ISBN to null. Errors return a JSON `error` field.

## Tests

Run `make test` to build and run the C unit tests. They cover input parsing and required fields, SQLite create and author filtering, JSON serialization, update, and delete behavior.
