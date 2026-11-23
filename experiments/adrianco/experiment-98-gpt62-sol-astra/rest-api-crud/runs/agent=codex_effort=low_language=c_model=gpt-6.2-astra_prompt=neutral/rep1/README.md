# Book collection API

This C11 service uses libevent for HTTP, json-c for JSON, and SQLite for storage.

## Build and run

Install a C compiler, Make, pkg-config, libevent 2.1, json-c 0.15 or newer, and SQLite 3.35 or newer with development headers. Python 3 runs the tests. On Debian or Ubuntu, the development packages are available with:

```sh
sudo apt install build-essential pkg-config libevent-dev libjson-c-dev libsqlite3-dev python3
```

Build the server and start it on the loopback interface:

```sh
make
./books
```

The default address is `http://127.0.0.1:8080`. SQLite creates `books.db` in the working directory. To choose a port and database path, run `./books 9000 ./collection.db`. Stop the server with Ctrl-C.

## API

| Method | Path | Successful JSON response |
| --- | --- | --- |
| GET | /health | 200 with `{"status":"ok"}` |
| POST | /books | 201 with the created book and a Location header |
| GET | /books | 200 with an array ordered by ID |
| GET | /books?author=Octavia%20Butler | 200 with exact, case-sensitive author matches |
| GET | /books/{id} | 200 with the book |
| PUT | /books/{id} | 200 with the replacement book |
| DELETE | /books/{id} | 200 with the deleted book |

Create and replace requests take a JSON object. Both require nonblank strings for `title` and `author`. The optional fields are an integer `year` and a string `isbn`. Omitted or null optional fields are stored as null, including on replacement. SQLite assigns each book a positive integer ID. Invalid book data returns 400, an unknown resource returns 404, and an unsupported method on a known route returns 405.

```sh
curl -i http://127.0.0.1:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Kindred","author":"Octavia Butler","year":1979,"isbn":"9780807083697"}'
curl --get http://127.0.0.1:8080/books --data-urlencode 'author=Octavia Butler'
```

## Tests

Run `make test` to exercise the production request handler with libevent request objects and temporary SQLite databases. The suite checks CRUD, persistence, author filtering, validation, health, and routing errors. Run `BOOKS_TEST_TCP=1 make test` to run the same assertions over HTTP against a local server.
