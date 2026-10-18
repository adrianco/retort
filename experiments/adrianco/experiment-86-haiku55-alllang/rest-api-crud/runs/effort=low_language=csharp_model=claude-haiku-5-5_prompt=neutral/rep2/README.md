# Book Collection API

A REST API for managing a book collection, built with ASP.NET Core minimal APIs (.NET 10) and SQLite via `Microsoft.Data.Sqlite`.

## Requirements

- .NET 10 SDK

## Setup

```bash
dotnet restore BookApi.slnx
```

## Run

```bash
dotnet run --project src/BookApi
```

The API listens on the ports configured in `Properties/launchSettings.json` (or the ASP.NET Core defaults). The SQLite database is created automatically at `books.db` in the working directory. To use a different file, set the connection string:

```bash
dotnet run --project src/BookApi -- --ConnectionStrings:Books="Data Source=/path/to/books.db"
```

## Test

```bash
dotnet test BookApi.slnx
```

## Endpoints

| Method | Path            | Description                                      | Success  |
|--------|-----------------|--------------------------------------------------|----------|
| GET    | `/health`       | Health check                                     | 200      |
| POST   | `/books`        | Create a book                                    | 201      |
| GET    | `/books`        | List books; optional `?author=` (case-insensitive exact match) | 200 |
| GET    | `/books/{id}`   | Get a book by ID                                 | 200      |
| PUT    | `/books/{id}`   | Replace a book's fields                          | 200      |
| DELETE | `/books/{id}`   | Delete a book                                    | 204      |

### Book fields

| Field    | Type    | Required | Rules                                                  |
|----------|---------|----------|--------------------------------------------------------|
| `title`  | string  | yes      | Non-blank, max 300 characters                          |
| `author` | string  | yes      | Non-blank, max 200 characters                          |
| `year`   | integer | no       | 1450 through next calendar year                        |
| `isbn`   | string  | no       | Valid ISBN-10 or ISBN-13; hyphens and spaces allowed   |

Responses for a book have the shape `{"id": 1, "title": "...", "author": "...", "year": 1965, "isbn": "9780441172719"}`. ISBNs are stored without hyphens.

### Examples

```bash
curl -i -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'

curl http://localhost:5000/books?author=Frank%20Herbert
curl -X PUT http://localhost:5000/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":null}'
curl -i -X DELETE http://localhost:5000/books/1
```

### Error responses

- `400 Bad Request` with an RFC 7807 problem body and an `errors` map when validation fails, or when the JSON body is malformed.
- `404 Not Found` with `{"error": "Book <id> was not found."}` for unknown IDs.

## Project layout

```
BookApi.slnx
src/BookApi/                 API: endpoints, validation, SQLite repository
tests/BookApi.Tests/         xUnit integration tests (WebApplicationFactory) and validator unit tests
```
