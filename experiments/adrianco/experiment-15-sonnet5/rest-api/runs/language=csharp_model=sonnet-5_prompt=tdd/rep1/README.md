# Book API

A REST API for managing a book collection, built with ASP.NET Core minimal APIs
and EF Core with a SQLite database.

## Requirements

- [.NET 10 SDK](https://dotnet.microsoft.com/download)

## Setup & run

```bash
cd BookApi
dotnet run
```

By default the API listens on the URL(s) printed at startup (e.g.
`http://localhost:5000`) and stores data in `BookApi/books.db`, a SQLite
file created automatically on first use.

To use a different database location, set the `ConnectionStrings:BookDb`
configuration value, e.g.:

```bash
dotnet run --ConnectionStrings:BookDb="Data Source=/path/to/other.db"
```

## Running tests

```bash
dotnet test
```

Tests are integration tests built on `WebApplicationFactory`, each running
against an isolated in-memory SQLite database.

## API

### Health check

`GET /health` → `200 OK`

```json
{ "status": "healthy" }
```

### Create a book

`POST /books`

Body:

```json
{ "title": "The Pragmatic Programmer", "author": "David Thomas", "year": 1999, "isbn": "978-0135957059" }
```

- `201 Created` with the created book (including its `id`) on success.
- `400 Bad Request` if `title` or `author` is missing/blank.

### List books

`GET /books`

- Returns `200 OK` with a JSON array of all books.
- Supports `?author=<name>` to filter by exact author match.

### Get a single book

`GET /books/{id}`

- `200 OK` with the book if found.
- `404 Not Found` if no book has that id.

### Update a book

`PUT /books/{id}`

Body: same shape as create.

- `200 OK` with the updated book on success.
- `400 Bad Request` if `title` or `author` is missing/blank.
- `404 Not Found` if no book has that id.

### Delete a book

`DELETE /books/{id}`

- `204 No Content` on success.
- `404 Not Found` if no book has that id.

## Project layout

- `BookApi/` — the API project (minimal API endpoints in `Program.cs`, `Book` entity, `BookDbContext`).
- `BookApi.Tests/` — xUnit integration tests covering health, create/validation, list/filter, get, update, and delete.
