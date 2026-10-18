# Book Collection API

A REST API for managing a book collection, built with ASP.NET Core minimal APIs (.NET 10) and SQLite via `Microsoft.Data.Sqlite`.

## Prerequisites

- [.NET 10 SDK](https://dotnet.microsoft.com/download)

## Project layout

```
BookApi.slnx                    Solution file
src/BookApi/                    API project (Program.cs, Book.cs, BookRepository.cs)
tests/BookApi.Tests/            xUnit integration tests
```

## Run

```bash
dotnet run --project src/BookApi
```

The API listens on the URL printed at startup (e.g. `http://localhost:5xxx`). The SQLite database is created automatically at `./books.db` in the working directory. To change it, set the connection string:

```bash
dotnet run --project src/BookApi -- --ConnectionStrings:Books="Data Source=/path/to/books.db"
```

## Test

```bash
dotnet test
```

The tests host the API in-process with `WebApplicationFactory` and use a temporary SQLite file per test class.

## Endpoints

| Method | Path          | Description                                   | Success | Errors            |
|--------|---------------|-----------------------------------------------|---------|-------------------|
| POST   | `/books`      | Create a book                                 | 201     | 400 (validation)  |
| GET    | `/books`      | List books; optional `?author=` filter        | 200     |                   |
| GET    | `/books/{id}` | Get one book                                  | 200     | 404               |
| PUT    | `/books/{id}` | Replace a book's fields                       | 200     | 400, 404          |
| DELETE | `/books/{id}` | Delete a book                                 | 204     | 404               |
| GET    | `/health`     | Health check (verifies the database is reachable) | 200 | 503 if DB unavailable |

### Book fields

| Field    | Type    | Required | Rules                                          |
|----------|---------|----------|------------------------------------------------|
| `title`  | string  | yes      | Non-blank, max 200 characters                  |
| `author` | string  | yes      | Non-blank, max 200 characters                  |
| `year`   | integer | no       | 1450 to next calendar year                     |
| `isbn`   | string  | no       | If provided, non-blank, max 17 characters      |

`id` is assigned by the server. `PUT` takes the full set of fields (it is a replacement, not a partial patch).

`?author=` matches the author exactly, ignoring case (e.g. `?author=isaac%20asimov`).

### Examples

```bash
# Create
curl -i -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

# List by author
curl "http://localhost:5000/books?author=Frank%20Herbert"

# Update
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":null}'

# Delete
curl -i -X DELETE http://localhost:5000/books/1
```

Validation failures return a standard `ValidationProblemDetails` body with an `errors` object keyed by field name.
