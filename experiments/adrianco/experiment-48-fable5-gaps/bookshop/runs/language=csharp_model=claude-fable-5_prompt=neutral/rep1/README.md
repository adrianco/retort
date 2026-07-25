# Book Collection API

A REST API for managing a book collection, built with ASP.NET Core minimal APIs (.NET 10) and SQLite (via `Microsoft.Data.Sqlite`).

## Project layout

```
BookApi/            The API service
  Program.cs        Endpoint definitions and app startup
  Book.cs           Book record and input validation
  BookRepository.cs SQLite data access (creates the schema on startup)
BookApi.Tests/      xUnit integration tests (in-process via WebApplicationFactory)
BookCollection.slnx Solution file
```

## Requirements

- .NET SDK 10.0 or later

## Run the service

```sh
dotnet run --project BookApi
```

The console prints the listening URL (e.g. `http://localhost:5123`). Data is stored in `books.db` in the working directory; override with a connection string:

```sh
dotnet run --project BookApi -- --ConnectionStrings:Books "Data Source=/path/to/books.db"
```

## Run the tests

```sh
dotnet test
```

The 11 integration tests spin up the app in-process against a temporary SQLite database, covering the health check, all CRUD operations, the author filter, validation errors (400), and not-found handling (404).

## API

| Method | Path                    | Description                          | Success | Errors |
|--------|-------------------------|--------------------------------------|---------|--------|
| GET    | `/health`               | Health check                         | 200     |        |
| POST   | `/books`                | Create a book                        | 201     | 400    |
| GET    | `/books`                | List books; `?author=` filters (case-insensitive exact match) | 200 | |
| GET    | `/books/{id}`           | Get one book                         | 200     | 404    |
| PUT    | `/books/{id}`           | Replace a book's fields              | 200     | 400, 404 |
| DELETE | `/books/{id}`           | Delete a book                        | 204     | 404    |

A book has `title` (required), `author` (required), `year` (optional integer, 0–9999), and `isbn` (optional string). Validation failures return `400` with a JSON body like `{"errors":["title is required"]}`; unknown IDs return `404` with `{"error":"book 7 not found"}`.

### Examples

```sh
# Create
curl -X POST http://localhost:5123/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'
# => 201 {"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}

# List, optionally filtered by author
curl 'http://localhost:5123/books?author=Frank%20Herbert'

# Get / update / delete
curl http://localhost:5123/books/1
curl -X PUT http://localhost:5123/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
curl -X DELETE http://localhost:5123/books/1   # => 204
```
