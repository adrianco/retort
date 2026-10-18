# Book Collection API

A small ASP.NET Core (.NET 10) REST service for managing a book collection, backed by SQLite.

## Prerequisites

- [.NET 10 SDK](https://dotnet.microsoft.com/download)

## Run

```bash
dotnet run --project BookApi.csproj
```

The API listens on the URL shown in the console output (for example `http://localhost:5000`).
The SQLite database is created automatically at `./books.db` on first start. To use a different file, set the connection string:

```bash
dotnet run --project BookApi.csproj -- --ConnectionStrings:Books="Data Source=/path/to/books.db"
```

## Test

```bash
dotnet test tests/BookApi.Tests/BookApi.Tests.csproj
```

The tests host the app in-process with `WebApplicationFactory` and use a temporary SQLite file per test.

## Endpoints

| Method | Path            | Description                                  | Success |
|--------|-----------------|----------------------------------------------|---------|
| POST   | `/books`        | Create a book                                | 201 Created (body + `Location`) |
| GET    | `/books`        | List books; optional `?author=` filter (case-insensitive exact match) | 200 OK |
| GET    | `/books/{id}`   | Get one book                                 | 200 OK |
| PUT    | `/books/{id}`   | Replace a book's fields                      | 200 OK |
| DELETE | `/books/{id}`   | Delete a book                                | 204 No Content |
| GET    | `/health`       | Health check (verifies the database is reachable) | 200 OK (503 if unhealthy) |

Unknown IDs return `404 Not Found`. Validation failures return `400 Bad Request` with a
`application/problem+json` body whose `errors` object is keyed by field name.

### Book fields

| Field    | Type    | Required | Rules |
|----------|---------|----------|-------|
| `title`  | string  | yes      | Non-blank |
| `author` | string  | yes      | Non-blank |
| `year`   | integer | yes      | Between 1450 and next calendar year |
| `isbn`   | string  | no       | If given, a valid ISBN-10 or ISBN-13 (hyphens and spaces are ignored and stored as digits) |

PUT requires the full set of fields (it replaces the record).

### Examples

```bash
curl -i -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'

curl "http://localhost:5000/books?author=Frank%20Herbert"

curl -i -X PUT http://localhost:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

curl -i -X DELETE http://localhost:5000/books/1
curl http://localhost:5000/health
```

## Project layout

- `Program.cs` — endpoint mapping and startup
- `Book.cs` — models and validation rules
- `BookRepository.cs` — SQLite data access (raw SQL via Microsoft.Data.Sqlite)
- `tests/BookApi.Tests/` — xUnit integration tests
