# Books API

A REST API for managing a book collection, built with C# / ASP.NET Core minimal APIs
and SQLite (`Microsoft.Data.Sqlite`).

## Requirements

- .NET SDK 10.0+

## Run

```bash
dotnet run --project src/BooksApi --urls http://localhost:5000
```

The SQLite database is created automatically as `books.db` in the working directory.
To use a different file, set the connection string:

```bash
ConnectionStrings__Books="Data Source=/path/to/books.db" dotnet run --project src/BooksApi
```

## Test

```bash
dotnet test
```

The integration tests host the API in-process, each against its own temporary SQLite file.

## Endpoints

| Method | Path          | Description                          | Success | Errors   |
|--------|---------------|--------------------------------------|---------|----------|
| GET    | `/health`     | Health check                         | 200     |          |
| POST   | `/books`      | Create a book                        | 201     | 400      |
| GET    | `/books`      | List books (optional `?author=`)     | 200     |          |
| GET    | `/books/{id}` | Get one book                         | 200     | 404      |
| PUT    | `/books/{id}` | Replace a book                       | 200     | 400, 404 |
| DELETE | `/books/{id}` | Delete a book                        | 204     | 404      |

Book JSON:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593" }
```

`title` and `author` are required and must be non-blank; `year` (0–9999) and `isbn` are optional.
Validation failures return 400 with a problem-details body listing the errors per field.
The `author` filter is an exact, case-insensitive match.

## Example

```bash
curl -X POST localhost:5000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl 'localhost:5000/books?author=Frank%20Herbert'
curl -X PUT localhost:5000/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -X DELETE localhost:5000/books/1
```
