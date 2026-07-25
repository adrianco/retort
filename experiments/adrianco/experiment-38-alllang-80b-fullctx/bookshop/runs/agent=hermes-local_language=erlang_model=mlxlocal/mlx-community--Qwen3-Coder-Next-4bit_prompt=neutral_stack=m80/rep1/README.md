# Book API REST Service

A REST API service for managing a book collection built with Erlang, Cowboy web server, and SQLite.

## Features

- POST /books - Create a new book (title, author, year, isbn)
- GET /books - List all books (support ?author= filter)
- GET /books/{id} - Get a single book by ID
- PUT /books/{id} - Update a book
- DELETE /books/{id} - Delete a book
- GET /health - Health check endpoint

## Requirements

- Erlang/OTP 24 or higher
- rebar3 (build tool)

## Setup

1. Clone this repository

2. Build the project:
```bash
rebar3 compile
```

3. Run tests:
```bash
rebar3 eunit
```

## Running the Server

1. Start the application:
```bash
rebar3 shell
```

2. Or start directly:
```bash
rebar3 run
```

The server will start on port 8080.

## API Usage Examples

### Create a book
```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}'
```

### List all books
```bash
curl http://localhost:8080/books
```

### List books by author
```bash
curl "http://localhost:8080/books?author=George%20Orwell"
```

### Get a single book
```bash
curl http://localhost:8080/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"1984 (Updated)"}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health check
```bash
curl http://localhost:8080/health
```

## Testing

Run all tests:
```bash
rebar3 eunit
```

Run specific test module:
```bash
rebar3 eunit -t book_api_db_tests
```

## Project Structure

```
src/
├── book_api_app.erl    # Application startup
├── book_api_sup.erl    # Supervisor
├── book_api_db.erl     # Database module (SQLite)
├── book_api_rest.erl   # REST API router
├── book_api_handler.erl # Request handlers
└── book_api_health.erl # Health check endpoint

test/
├── book_api_db_tests.erl           # Unit tests for DB
├── book_api_integration_tests.erl  # Integration tests
└── book_api_tests.erl              # Test runner
```

## License

MIT
