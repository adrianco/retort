# Book API REST Service

A REST API service for managing a book collection built with Elixir and Phoenix.

## Features

- Create, read, update, and delete books
- Author-based filtering
- SQLite database for data persistence
- Input validation
- Health check endpoint

## Requirements

- Elixir 1.18+
- Erlang/OTP 25+

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

4. Run the application:

```bash
mix phx.server
```

The server will start on `http://localhost:4000`.

## API Endpoints

### Health Check

```
GET /api/health
```

Response:
```json
{
  "status": "healthy"
}
```

### List Books

```
GET /api/books
GET /api/books?author=Author%20Name
```

### Get Single Book

```
GET /api/books/:id
```

### Create Book

```
POST /api/books
Content-Type: application/json

{
  "title": "Book Title",
  "author": "Author Name",
  "year": 2024,
  "isbn": "1234567890"
}
```

### Update Book

```
PUT /api/books/:id
Content-Type: application/json

{
  "title": "Updated Title",
  "author": "Updated Author",
  "year": 2025,
  "isbn": "1234567890"
}
```

### Delete Book

```
DELETE /api/books/:id
```

## Testing

Run the test suite:

```bash
mix test
```

To run tests with coverage:

```bash
mix cover.html
```

## Project Structure

```
book_api/
├── lib/
│   ├── book_api/
│   │   ├── application.ex
│   │   ├── book.ex
│   │   ├── repo.ex
│   │   ├── release.ex
│   │   └── web/
│   │       ├── controllers/
│   │       │   ├── book_controller.ex
│   │       │   └── health_controller.ex
│   │       ├── endpoint.ex
│   │       ├── gettext.ex
│   │       └── router.ex
├── priv/
│   └── repo/
│       ├── migrations/
│       └── seeds.exs
├── test/
│   └── book_api/
│       └── book_controller_test.exs
├── mix.exs
└── README.md
```

## License

MIT License
