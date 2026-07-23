# Book API REST Service

A REST API service for managing a book collection built with Erlang.

## Features

- POST /books - Create a new book
- GET /books - List all books (supports ?author= filter)
- GET /books/{id} - Get a single book by ID
- PUT /books/{id} - Update a book
- DELETE /books/{id} - Delete a book
- GET /health - Health check endpoint

## Prerequisites

- Erlang/OTP 24 or higher
- rebar3 build tool

## Building

```bash
rebar3 compile
```

## Running Tests

```bash
make test
```

Or directly with rebar3:

```bash
rebar3 eunit
```

## Running the Server

### Using Makefile

```bash
make run
```

### Manual start

```bash
rebar3 shell
```

Then in the Erlang shell:

```erlang
application:ensure_all_started(book_api).
```

The server will start on port 8080.

## API Usage Examples

### Create a book

```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"}'
```

### List all books

```bash
curl http://localhost:8080/books
```

### List books by author

```bash
curl "http://localhost:8080/books?author=Fitzgerald"
```

### Get a specific book

```bash
curl http://localhost:8080/books/1
```

### Update a book

```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby (Updated)"}'
```

### Delete a book

```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health check

```bash
curl http://localhost:8080/health
```

## Project Structure

```
.
├── rebar.config          # Dependencies and build configuration
├── Makefile              # Convenience targets
├── src/
│   ├── book_api.app.src  # Application specification
│   ├── book_api_app.erl  # Application start/stop
│   ├── book_api_sup.erl  # Supervisor
│   ├── book_api_db.erl   # Database module with CRUD operations
│   ├── book_api_routes.erl # Cowboy HTTP handlers
│   └── book_api_db.hrl   # Record definitions
├── test/
│   └── book_api_unit_tests.erl # Unit tests
└── README.md             # This file
```

## License

MIT License
