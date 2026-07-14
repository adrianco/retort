# Book Collection API

A REST API for managing a book collection, built with **ASP.NET Core Minimal APIs**
(.NET 10), **Entity Framework Core**, and **SQLite** for storage.

## Project layout

```
src/BookApi/           # The web API
  Program.cs           # Endpoint definitions and app wiring
  Models/Book.cs       # Book entity + BookInput DTO
  Data/BookDbContext.cs# EF Core DbContext
tests/BookApi.Tests/   # xUnit integration tests (BDD style)
BookCollection.slnx    # Solution file
```

## Prerequisites

- [.NET SDK 10.0](https://dotnet.microsoft.com/download) or later

## Setup & run

```bash
# Restore and build
dotnet build

# Run the API (creates books.db automatically on first start)
dotnet run --project src/BookApi
```

By default the service listens on the URL printed in the console
(e.g. `http://localhost:5000`). The SQLite database file `books.db` is created
in the working directory. Override the connection string with:

```bash
export ConnectionStrings__Books="Data Source=/path/to/mybooks.db"
```

## Running the tests

```bash
dotnet test
```

The integration tests boot the real API against a private in-memory SQLite
database, so they need no external setup and leave no files behind.

## API reference

| Method | Path            | Description                                | Success       |
|--------|-----------------|--------------------------------------------|---------------|
| GET    | `/health`       | Health check                               | `200 OK`      |
| POST   | `/books`        | Create a book                              | `201 Created` |
| GET    | `/books`        | List books (optional `?author=` filter)    | `200 OK`      |
| GET    | `/books/{id}`   | Get a book by id                           | `200 OK`      |
| PUT    | `/books/{id}`   | Update a book                              | `200 OK`      |
| DELETE | `/books/{id}`   | Delete a book                              | `204 No Content` |

### Book fields

| Field    | Type    | Required |
|----------|---------|----------|
| `title`  | string  | yes      |
| `author` | string  | yes      |
| `year`   | integer | no       |
| `isbn`   | string  | no       |

Requests missing `title` or `author` return `400 Bad Request` with a
validation-problem body. Unknown ids return `404 Not Found`.

### Examples

```bash
# Create a book
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Pragmatic Programmer","author":"Andrew Hunt","year":1999,"isbn":"978-0201616224"}'

# List all books
curl http://localhost:5000/books

# Filter by author
curl "http://localhost:5000/books?author=Andrew%20Hunt"

# Get one book
curl http://localhost:5000/books/1

# Update a book
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Pragmatic Programmer, 2nd Ed","author":"Andrew Hunt","year":2019,"isbn":"978-0135957059"}'

# Delete a book
curl -X DELETE http://localhost:5000/books/1
```
