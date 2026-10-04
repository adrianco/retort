# Books API

A REST API for managing a book collection, built with C# / ASP.NET Core minimal APIs (.NET 10) and SQLite (`Microsoft.Data.Sqlite`).

## Requirements

- [.NET SDK 10](https://dotnet.microsoft.com/download)

## Run

```bash
dotnet run --project src/BooksApi --urls http://localhost:5000
```

Data is stored in a SQLite file, `books.db` in the working directory by default (created on first use).
Override the location with the `DbPath` setting:

```bash
DbPath=/tmp/books.db dotnet run --project src/BooksApi --urls http://localhost:5000
```

## Test

```bash
dotnet test
```

The integration tests host the API in-process and run each test against its own temporary SQLite file.

## Endpoints

| Method | Path          | Description                              | Success | Errors     |
|--------|---------------|------------------------------------------|---------|------------|
| GET    | `/health`     | Health check                             | 200     |            |
| POST   | `/books`      | Create a book                            | 201     | 400        |
| GET    | `/books`      | List books; optional `?author=` filter   | 200     |            |
| GET    | `/books/{id}` | Get one book                             | 200     | 404        |
| PUT    | `/books/{id}` | Replace a book                           | 200     | 400, 404   |
| DELETE | `/books/{id}` | Delete a book                            | 204     | 404        |

Book JSON:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593" }
```

- `title` and `author` are required and must not be blank; `year` (0–9999) and `isbn` are optional.
- Validation failures return `400` with a problem-details body whose `errors` object is keyed by field.
- The `author` filter is an exact, case-insensitive match.
- `PUT` replaces the whole book, so omitted optional fields are cleared.

## Example

```bash
curl -i -X POST localhost:5000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl 'localhost:5000/books?author=Frank%20Herbert'
curl -X PUT localhost:5000/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -i -X DELETE localhost:5000/books/1
```

## Layout

- `src/BooksApi/Program.cs` — routes
- `src/BooksApi/Book.cs` — model and input validation
- `src/BooksApi/BookStore.cs` — SQLite storage
- `tests/BooksApi.Tests/` — xUnit integration tests
