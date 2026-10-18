# Book Collection REST API (C++)

A small JSON REST service backed by SQLite. It uses a minimal POSIX TCP HTTP server and the SQLite C API, so no additional HTTP or JSON framework is required.

## Build and run

Requirements: C++17 compiler, CMake 3.16+, and SQLite development headers/library.

```sh
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
./build/book_server                 # listens on port 8080
```

Set `PORT` to choose a port and `BOOKS_DB` to choose the SQLite file. The server also accepts the port as its first command-line argument.

## Endpoints

- `GET /health` — returns `{"status":"ok"}`.
- `POST /books` — creates a book from JSON fields `title` and `author` (required), plus optional `year` and `isbn`; returns `201` and the created record.
- `GET /books` — returns all books; `GET /books?author=Frank%20Herbert` filters by exact author.
- `GET /books/{id}` — returns one book or `404`.
- `PUT /books/{id}` — replaces book fields; `title` and `author` are required; returns the updated record or `404`.
- `DELETE /books/{id}` — deletes a book; returns `204` or `404`.

Malformed JSON and invalid required fields return `400`. Book records are JSON objects with `id`, `title`, `author`, `year`, and `isbn`; unspecified optional fields are `null`.
