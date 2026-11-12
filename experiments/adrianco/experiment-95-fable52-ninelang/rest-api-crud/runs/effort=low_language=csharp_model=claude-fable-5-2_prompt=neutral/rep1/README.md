# Book Collection API

A REST API for managing a book collection, built with C# / ASP.NET Core minimal APIs (.NET 10) and SQLite (`Microsoft.Data.Sqlite`).

## Requirements

- .NET SDK 10.0+

## Run

```bash
dotnet run --project src/BookApi --urls http://localhost:5000
```

Data is stored in `books.db` in the working directory (created automatically). To use a different file:

```bash
ConnectionStrings__Books="Data Source=/path/to/books.db" dotnet run --project src/BookApi
```

## Test

```bash
dotnet test
```

Integration tests run the real app in-process against a temporary SQLite file per test.

## Endpoints

| Method | Path          | Description                              | Success | Errors   |
|--------|---------------|------------------------------------------|---------|----------|
| GET    | `/health`     | Health check                             | 200     |          |
| POST   | `/books`      | Create a book                            | 201     | 400      |
| GET    | `/books`      | List books; `?author=` filters (exact, case-insensitive) | 200 | |
| GET    | `/books/{id}` | Get one book                             | 200     | 404      |
| PUT    | `/books/{id}` | Replace a book                           | 200     | 400, 404 |
| DELETE | `/books/{id}` | Delete a book                            | 204     | 404      |

Book JSON:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593" }
```

`title` and `author` are required and must be non-blank; `year` (integer) and `isbn` (string) are optional. Validation failures and malformed JSON return 400 with a problem-details body.

## Example

```bash
curl -X POST localhost:5000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl 'localhost:5000/books?author=Frank%20Herbert'
```
