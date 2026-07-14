# Book Collection API

A REST API for managing a book collection, built with ASP.NET Core (minimal APIs) and
Entity Framework Core with SQLite.

## Project layout

```
BookCollection.slnx
src/BookCollection.Api/      # the API project
tests/BookCollection.Tests/  # xUnit integration tests
```

## Requirements

- [.NET 10 SDK](https://dotnet.microsoft.com/download)

## Setup & run

From the repository root:

```bash
dotnet restore
dotnet run --project src/BookCollection.Api
```

The API listens on the URL printed at startup (e.g. `http://localhost:5xxx`). On first run it
creates a SQLite database file (`books.db`) in the project's working directory automatically —
no migrations step is required.

You can change the database location via the `ConnectionStrings:BooksDb` setting in
`src/BookCollection.Api/appsettings.json` or an environment variable
(`ConnectionStrings__BooksDb`).

## Running the tests

```bash
dotnet test
```

The test suite spins up the API in-memory (via `WebApplicationFactory`) against a fresh
in-memory SQLite database per test, so it does not touch the real `books.db` file.

## API

### Health check

```
GET /health
```

Returns `200 OK` with `{ "status": "healthy" }`.

### Create a book

```
POST /books
Content-Type: application/json

{
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441013593"
}
```

- `title` and `author` are required (`400 Bad Request` with validation errors if missing).
- `year` and `isbn` are optional.
- Returns `201 Created` with the created book (including its generated `id`) and a `Location` header.

### List books

```
GET /books
GET /books?author=Herbert
```

Returns `200 OK` with a JSON array of books. The optional `author` query parameter filters
results to authors whose name contains the given value (case-insensitive, partial match).

### Get a book by ID

```
GET /books/{id}
```

Returns `200 OK` with the book, or `404 Not Found` if no book exists with that ID.

### Update a book

```
PUT /books/{id}
Content-Type: application/json

{
  "title": "Dune Messiah",
  "author": "Frank Herbert",
  "year": 1969,
  "isbn": "9780441172696"
}
```

Replaces the book's fields. `title` and `author` are required. Returns `200 OK` with the
updated book, or `404 Not Found` if no book exists with that ID.

### Delete a book

```
DELETE /books/{id}
```

Returns `204 No Content` on success, or `404 Not Found` if no book exists with that ID.

## Book shape

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441013593"
}
```
