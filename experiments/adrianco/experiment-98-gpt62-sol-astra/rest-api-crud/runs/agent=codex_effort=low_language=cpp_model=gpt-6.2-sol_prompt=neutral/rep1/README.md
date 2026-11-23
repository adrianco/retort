# Book collection API

A C++17 REST service using libevent for HTTP, json-c for JSON, and SQLite for persistence.

## Setup

Install a C++17 compiler, CMake, pkg-config, libevent, json-c 0.15 or newer, and SQLite development headers. On macOS with the Xcode command-line tools, the SDK supplies SQLite.

```sh
brew install cmake pkg-config libevent json-c
```

On Debian or Ubuntu:

```sh
sudo apt-get install build-essential cmake pkg-config libevent-dev libjson-c-dev libsqlite3-dev
```

## Build and run

```sh
cmake -S . -B build
cmake --build build
./build/books_api
```

The service listens on `127.0.0.1:8080` and creates `books.db` in the working directory. To use a different port and database file, run `./build/books_api 9000 collection.db`.

## API

| Method | Path | Successful response |
| --- | --- | --- |
| GET | `/health` | `200` with `{"status":"ok"}` |
| POST | `/books` | `201` with the created book and a `Location` header |
| GET | `/books` | `200` with books ordered by ID |
| GET | `/books?author=Octavia%20Butler` | `200` with books matching the author exactly, including case |
| GET | `/books/{id}` | `200` with the book |
| PUT | `/books/{id}` | `200` with the replacement book |
| DELETE | `/books/{id}` | `204` with an empty body |

POST and PUT accept a JSON object with non-blank string fields `title` and `author`. The optional `year` is an integer and the optional `isbn` is a string. Both accept `null`. Omitting them in a PUT clears them. Each returned book includes a server-assigned integer `id`. Invalid input returns `400` with a JSON error. Unknown routes and missing books return `404`.

```sh
curl -i http://127.0.0.1:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Kindred","author":"Octavia Butler","year":1979,"isbn":"9780807083697"}'

curl 'http://127.0.0.1:8080/books?author=Octavia%20Butler'
```

## Tests

```sh
ctest --test-dir build --output-on-failure
```

Five tests exercise the request dispatcher and SQLite in process, covering health, the CRUD lifecycle, author filtering, input validation, and persistence after reopening the database.
