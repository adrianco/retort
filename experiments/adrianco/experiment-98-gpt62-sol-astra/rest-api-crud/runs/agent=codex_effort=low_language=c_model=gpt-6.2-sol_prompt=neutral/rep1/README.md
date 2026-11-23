# Book Collection API

A C REST service using Libevent, json-c, and SQLite.

## Build and run

Install a C11 compiler, Make, pkg-config, Libevent 2.1, json-c 0.15 or newer, and SQLite 3.35 or newer.

- macOS with Homebrew `brew install pkgconf libevent json-c sqlite`
- Debian or Ubuntu `sudo apt install build-essential pkg-config libevent-dev libjson-c-dev libsqlite3-dev`

```sh
make
./book-api [port] [database-file]
```

The service listens on `127.0.0.1`. The default port is `8080`, and the default database is `books.db` in the working directory. SQLite creates the database on first run.

## Endpoints

| Method | Path | Successful response |
| --- | --- | --- |
| GET | `/health` | 200 with `{"status":"ok"}` |
| POST | `/books` | 201 with the created book and a `Location` header |
| GET | `/books` | 200 with books ordered by ID |
| GET | `/books/{id}` | 200 with the requested book |
| PUT | `/books/{id}` | 200 with the replacement book |
| DELETE | `/books/{id}` | 204 with an empty body |

Use `GET /books?author=Octavia%20Butler` for an exact, case-sensitive author match. An empty collection or a filter with no matches returns `[]`.

POST and PUT accept a JSON object with nonblank string fields `title` and `author`. The optional `year` accepts a signed 32-bit integer or null. The optional `isbn` accepts a string or null. Omitted optional fields become null, including on PUT. The service assigns the book's numeric `id`. Invalid input returns 400, missing books return 404, and unsupported methods on an endpoint return 405. API errors have an `error` field containing a message.

```sh
curl -i -X POST http://127.0.0.1:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Kindred","author":"Octavia Butler","year":1979,"isbn":"9780807083697"}'
```

## Tests

Run `make test` for five C tests that exercise routing, CRUD, filtering, validation, and SQLite persistence without opening a network socket.

Run `make test-http` for the end-to-end suite. It requires Python 3.11 or newer and permission to bind a local TCP port.
