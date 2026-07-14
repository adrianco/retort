# Book Collection API

A REST API for managing a book collection, built with ASP.NET Core 10 and SQLite.

## Prerequisites

- [.NET 10 SDK](https://dotnet.microsoft.com/download)

## Setup and Run

```bash
cd BookCollection.Api
dotnet run
```

The API starts on `http://localhost:5000` (or `https://localhost:5001`).

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| GET | /books | List all books (supports `?author=` filter) |
| GET | /books/{id} | Get a book by ID |
| POST | /books | Create a new book |
| PUT | /books/{id} | Update a book |
| DELETE | /books/{id} | Delete a book |

### Create a book

```bash
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Go Programming Language", "author": "Alan Donovan", "year": 2015, "isbn": "978-0134190440"}'
```

`title` and `author` are required. `year` and `isbn` are optional.

### List books with author filter

```bash
curl "http://localhost:5000/books?author=Alan+Donovan"
```

## Running Tests

```bash
dotnet test
```

Tests use an in-memory SQLite database — no setup required.

## Configuration

The SQLite database file defaults to `books.db` in the working directory. Override via `appsettings.json`:

```json
{
  "ConnectionStrings": {
    "DefaultConnection": "Data Source=/path/to/books.db"
  }
}
```
