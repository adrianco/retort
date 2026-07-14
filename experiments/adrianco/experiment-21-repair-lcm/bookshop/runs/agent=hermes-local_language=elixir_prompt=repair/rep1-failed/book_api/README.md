# Book API - REST API for Managing a Book Collection

A REST API service built with Elixir, Plug, Ecto, and SQLite3 for managing a book collection.

## Features

- POST /books — Create a new book (title, author, year, isbn)
- GET /books — List all books (supports ?author= filter)
- GET /books/:id — Get a single book by ID
- PUT /books/:id — Update a book
- DELETE /books/:id — Delete a book
- GET /health — Health check endpoint

## Technical Stack

- **Elixir 1.20+** - Programming language
- **Plug + Cowboy** - HTTP server and router
- **Ecto + SQLite3** - Database and ORM
- **Jason** - JSON encoding/decoding

## Prerequisites

- Elixir 1.20 or later
- Erlang/OTP 24 or later

## Setup and Run

### 1. Install Dependencies

```bash
mix deps.get
```

### 2. Set Up Database

Create the database directory and run migrations:

```bash
mkdir -p tmp/db
mix ecto.migrate
```

### 3. Start the Server

```bash
mix run --no-halt
```

Or to run in the interactive shell:

```bash
iex -S mix
```

The server will start on `http://localhost:4000`.

## API Endpoints

### Health Check
```bash
curl http://localhost:4000/health
```

Response:
```json
{"status":"healthy"}
```

### Create a Book
```bash
curl -X POST http://localhost:4000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}'
```

Response (201 Created):
```json
{"id":1,"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}
```

### List All Books
```bash
curl http://localhost:4000/books
```

Response (200 OK):
```json
{"books":[{"id":1,"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}]}
```

### Filter Books by Author
```bash
curl "http://localhost:4000/books?author=Fitzgerald"
```

### Get a Book by ID
```bash
curl http://localhost:4000/books/1
```

### Update a Book
```bash
curl -X PUT http://localhost:4000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby (Updated)"}'
```

### Delete a Book
```bash
curl -X DELETE http://localhost:4000/books/1
```

## Running Tests

```bash
mix test
```

## Project Structure

```
book_api/
├── lib/
│   ├── book_api/
│   │   ├── application.ex    # Application supervisor
│   │   ├── repo.ex            # Ecto repository
│   │   ├── router.ex          # Plug router (API endpoints)
│   │   └── books/
│   │       └── book.ex        # Book schema
│   └── book_api.ex            # Main module
├── priv/
│   └── repo/
│       └── migrations/
│           └── *.exs          # Database migrations
├── config/
│   ├── config.exs             # Main configuration
│   └── test.exs               # Test configuration
├── test/
│   ├── book_api_test.exs      # Test suite
│   └── test_helper.exs        # Test setup
├── mix.exs                    # Project configuration
└── README.md
```
