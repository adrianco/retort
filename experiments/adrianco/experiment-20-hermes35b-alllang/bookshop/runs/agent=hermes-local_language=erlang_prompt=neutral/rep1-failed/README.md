# Book Collection REST API

A REST API service for managing a book collection, built with Erlang and Cowboy.

## Features

- **POST /books** - Create a new book (title, author, year, isbn)
- **GET /books** - List all books (with optional `?author=` filter)
- **GET /books/:id** - Get a single book by ID
- **PUT /books/:id** - Update a book
- **DELETE /books/:id** - Delete a book
- **GET /health** - Health check endpoint

## Technical Stack

- **Language**: Erlang/OTP 29
- **HTTP Server**: Cowboy
- **JSON**: Jiffy
- **Storage**: ETS (Erlang Term Storage) - Erlang's built-in embedded in-memory database
- **Build Tool**: Rebar3

## Prerequisites

- Erlang/OTP 23+
- Rebar3

## Building

```bash
rebar3 compile
```

## Running

```bash
# Start the application
rebar3 shell

# Or run as a standalone application
rebar3 exec -- erl -noshell -s book_api start
```

The API server will start on port 8080.

## Usage Examples

### Health Check
```bash
curl http://localhost:8080/health
# Response: {"status":"ok"}
```

### Create a Book
```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"Programming Erlang","author":"Joe Armstrong","year":2013,"isbn":"978-1593271134"}'
```

### List All Books
```bash
curl http://localhost:8080/books
```

### List Books by Author
```bash
curl "http://localhost:8080/books?author=Joe%20Armstrong"
```

### Get a Book
```bash
curl http://localhost:8080/books/1
```

### Update a Book
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Updated Title"}'
```

### Delete a Book
```bash
curl -X DELETE http://localhost:8080/books/1
```

## Running Tests

### Unit Tests (book_db)
```bash
# Compile
rebar3 compile

# Run unit tests
erl -noshell -pa ebin -pa src -s book_db_tests main
```

### Integration Tests (HTTP API)
```bash
# Compile
rebar3 compile

# Run integration tests
erl -noshell -pa ebin -pa src -s integration_tests main
```

## API Response Examples

### Create Book (201 Created)
```json
{
  "id": 1,
  "title": "Programming Erlang",
  "author": "Joe Armstrong",
  "year": 2013,
  "isbn": "978-1593271134"
}
```

### List Books (200 OK)
```json
{
  "books": [
    {
      "id": 1,
      "title": "Programming Erlang",
      "author": "Joe Armstrong",
      "year": 2013,
      "isbn": "978-1593271134"
    }
  ]
}
```

### Error Response (400 Bad Request)
```json
{
  "error": "title and author are required"
}
```

## Project Structure

```
.
├── rebar.config
├── README.md
├── src/
│   ├── book_api.app.src
│   ├── book_api.erl           # Application module
│   ├── book_api_sup.erl       # Supervisor
│   ├── book_db.erl            # Database layer (gen_server + ETS)
│   └── book_api_handler.erl   # Cowboy HTTP handler
└── test/
    ├── book_db_tests.erl      # Unit tests for database layer
    └── integration_tests.erl  # Integration tests for HTTP API
```
