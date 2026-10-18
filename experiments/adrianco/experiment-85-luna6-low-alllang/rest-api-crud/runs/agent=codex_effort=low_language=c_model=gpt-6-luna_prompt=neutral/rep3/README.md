# Book Collection API

A small C REST API backed by SQLite and POSIX sockets.

## Requirements

- C compiler
- SQLite development library
- SQLite development library
- Python 3 (for integration tests)

On Debian or Ubuntu, install the library with `sudo apt install build-essential libsqlite3-dev`.

## Build and run

```sh
make
./book_service
```

The service listens on port 8080. Set `PORT` to change the port and `BOOKS_DB` to select the SQLite database file. The database table is created at startup.

## API

- `GET /health` — returns `{"status":"ok"}`
- `POST /books` — JSON body: `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`; returns 201
- `GET /books` — list books; optionally filter with `?author=Frank%20Herbert`
- `GET /books/{id}` — fetch one book
- `PUT /books/{id}` — replace title, author, year, and isbn; returns updated book
- `DELETE /books/{id}` — delete a book; returns a confirmation object

Title and author are required. Year is an integer from 0 to 9999 and isbn is optional. Errors are JSON. Missing books return 404 and invalid input returns 400.

## Tests

```sh
make test
```
