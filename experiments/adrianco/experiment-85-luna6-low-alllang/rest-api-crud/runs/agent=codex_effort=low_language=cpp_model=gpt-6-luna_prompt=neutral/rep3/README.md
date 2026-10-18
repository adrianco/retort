# Book Collection API

A small C++17 REST service backed by SQLite. It uses the system SQLite library and `json-c` for JSON parsing and serialization.

## Build

Requirements: CMake, a C++17 compiler, SQLite development files, `pkg-config`, and `json-c`.

```sh
cmake -S . -B build
cmake --build build
```

## Run

```sh
./build/book_api
```

The server listens on port 8080. Set `PORT` to change the port and `BOOKS_DB` to choose the SQLite database path.

Endpoints: `GET /health`; `POST /books` with JSON `{ "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593" }`; `GET /books?author=Frank%20Herbert`; `GET /books/{id}`; `PUT /books/{id}` with the same JSON fields; and `DELETE /books/{id}`. Title and author are required and cannot be blank. Successful creation returns 201, missing books return 404, invalid requests return 400, and delete returns 204.

## Tests

```sh
cmake --build build
ctest --test-dir build --output-on-failure
```
