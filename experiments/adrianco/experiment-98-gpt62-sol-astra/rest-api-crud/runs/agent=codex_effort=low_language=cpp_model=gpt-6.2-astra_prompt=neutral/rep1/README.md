# Book collection API

Build with a C++17 compiler, CMake 3.16+, Boost 1.75+ (Beast and JSON), and SQLite development headers and library. The integration tests use Python 3. On macOS with Xcode command line tools, install the additional dependencies with `brew install cmake boost python`.

```sh
cmake -S . -B build
cmake --build build
(cd build && ctest --output-on-failure)
./build/book_api 8080 books.sqlite3
```

The server listens on 127.0.0.1. Both arguments are optional and default to the values shown. SQLite creates the database on first use.

```sh
curl -i http://127.0.0.1:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"Kindred","author":"Octavia Butler","year":1979,"isbn":"9780807083697"}'
curl 'http://127.0.0.1:8080/books?author=Octavia+Butler'
```

| Method | Path | Result |
| --- | --- | --- |
| GET | /health | Service status |
| POST | /books | Created book with assigned ID (201) |
| GET | /books | Array ordered by ID, optionally filtered by exact author |
| GET | /books/{id} | Single book |
| PUT | /books/{id} | Replace the book fields and return the updated book |
| DELETE | /books/{id} | Delete the book and return its ID |

POST and PUT require nonblank title and author strings. Optional fields are an integer year and a string ISBN. Omitted or null optional fields are stored as null. Responses use JSON. Invalid input returns 400, a missing book or route returns 404, and an unsupported method on a known route returns 405.
