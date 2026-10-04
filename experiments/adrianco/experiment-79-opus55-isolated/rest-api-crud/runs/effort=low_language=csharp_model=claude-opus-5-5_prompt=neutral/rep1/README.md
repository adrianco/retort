# Book Collection API

A REST API for managing a book collection, built with C# / ASP.NET Core minimal APIs (.NET 10)
and SQLite (`Microsoft.Data.Sqlite`).

## Layout

- `src/BookApi` — the API service
- `tests/BookApi.Tests` — xUnit integration tests (run the real app in-process against a temporary SQLite file)

## Setup and run

Requires the [.NET 10 SDK](https://dotnet.microsoft.com/download).

```bash
dotnet build
dotnet run --project src/BookApi --urls http://localhost:5000
```

The database file (`books.db` by default, relative to the working directory) and its schema are
created automatically. Override the location with the `Database:Path` setting, e.g.:

```bash
Database__Path=/tmp/books.db dotnet run --project src/BookApi
```

## Tests

```bash
dotnet test
```

## Endpoints

| Method | Path          | Description                          | Success | Errors     |
|--------|---------------|--------------------------------------|---------|------------|
| GET    | `/health`     | Health check (verifies DB access)    | 200     | 503        |
| POST   | `/books`      | Create a book                        | 201     | 400        |
| GET    | `/books`      | List books; optional `?author=`      | 200     |            |
| GET    | `/books/{id}` | Get one book                         | 200     | 404        |
| PUT    | `/books/{id}` | Replace a book                       | 200     | 400, 404   |
| DELETE | `/books/{id}` | Delete a book                        | 204     | 404        |

Book JSON:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593" }
```

Validation rules:

- `title` and `author` are required and must not be blank.
- `year` is optional; if given it must be an integer between 0 and 9999.
- `isbn` is optional and stored as given (no format or uniqueness check).
- The `?author=` filter is an exact, case-insensitive match.

Validation failures return `400` with a problem-details body containing an `errors` object keyed
by field. Malformed JSON returns `400` with `{"error": "..."}`; unknown IDs return `404` with
`{"error": "..."}`.

## Example

```bash
curl -i -X POST localhost:5000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl 'localhost:5000/books?author=Frank%20Herbert'
curl -X PUT localhost:5000/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
curl -i -X DELETE localhost:5000/books/1
```
