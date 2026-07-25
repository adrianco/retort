# Book API REST Service

A REST API service for managing a book collection built with Elixir and Phoenix framework using SQLite as the database.

## Features

- **Health Check**: `GET /api/health`
- **Create Book**: `POST /api/books`
- **List Books**: `GET /api/books` (with optional `?author=` filter)
- **Get Book**: `GET /api/books/{id}`
- **Update Book**: `PUT /api/books/{id}`
- **Delete Book**: `DELETE /api/books/{id}`

## Requirements

- Elixir 1.20 or higher
- Erlang/OTP 26 or higher
- SQLite3

## Installation

1. Navigate to the project directory:

```bash
cd book_api
```

2. Install dependencies:

```bash
mix deps.get
```

3. Create and migrate the database:

```bash
mix ecto.create
mix ecto.migrate
```

4. Run the server:

```bash
mix phx.server
```

The server will start on `http://localhost:4000`.

## API Endpoints

### Health Check

```bash
curl http://localhost:4000/api/health
```

Response:
```json
{
  "status": "ok",
  "service": "book-api"
}
```

### List Books

```bash
curl http://localhost:4000/api/books
```

With author filter:
```bash
curl "http://localhost:4000/api/books?author=John"
```

### Get Book by ID

```bash
curl http://localhost:4000/api/books/1
```

### Create Book

```bash
curl -X POST http://localhost:4000/api/books \
  -H "Content-Type: application/json" \
  -d '{
    "book": {
      "title": "The Great Gatsby",
      "author": "F. Scott Fitzgerald",
      "year": 1925,
      "isbn": "978-0743273565"
    }
  }'
```

### Update Book

```bash
curl -X PUT http://localhost:4000/api/books/1 \
  -H "Content-Type: application/json" \
  -d '{
    "book": {
      "title": "The Great Gatsby (Updated)",
      "author": "F. Scott Fitzgerald",
      "year": 1925,
      "isbn": "978-0743273565"
    }
  }'
```

### Delete Book

```bash
curl -X DELETE http://localhost:4000/api/books/1
```

## Validation

The API validates the following:
- `title` and `author` are required
- `title` and `author` must be between 1 and 255 characters
- `isbn` must be 10-20 characters and contain only numbers, hyphens, or 'X'

## Error Responses

The API returns appropriate HTTP status codes:
- `200 OK` - Success
- `201 Created` - Resource created
- `204 No Content` - Resource deleted
- `404 Not Found` - Resource not found
- `422 Unprocessable Entity` - Validation errors

Example error response:
```json
{
  "errors": {
    "detail": "Book not found"
  }
}
```

## Testing

Run the test suite:

```bash
mix test
```

Run tests with coverage:

```bash
mix coveralls.html
```

## Project Structure

```
book_api/
├── lib/
│   ├── book_api/
│   │   ├── application.ex
│   │   ├── book.ex
│   │   ├── repo.ex
│   │   └── repo/
│   │       └── migrations/
│   └── book_api_web/
│       ├── controllers/
│       │   ├── book_controller.ex
│       │   ├── fallback_controller.ex
│       │   └── health_controller.ex
│       ├── views/
│       │   ├── book_view.ex
│       │   ├── health_view.ex
│       │   └── error_view.ex
│       ├── endpoint.ex
│       ├── router.ex
│       └── telemetry.ex
├── config/
│   ├── config.exs
│   ├── dev.exs
│   ├── prod.exs
│   └── test.exs
├── test/
│   ├── book_api/
│   │   ├── book_test.exs
│   │   └── data_case.ex
│   └── book_api_web/
│       ├── controllers/
│       │   ├── book_controller_test.exs
│       │   └── health_controller_test.exs
│       └── conn_case.ex
├── mix.exs
└── README.md
```

## License

MIT License
