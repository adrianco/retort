# Book Collection API

A minimal ASP.NET Core REST API that stores books in a local SQLite database.

## Requirements

- .NET 10 SDK
- SQLite native library (`sqlite3`), included with macOS and most Linux distributions

## Run

From the workspace root:

```sh
dotnet run --project BookCollection.Api
```

The API listens on the URL shown by ASP.NET Core (typically `http://localhost:5000` or `http://localhost:5001`). It creates `books.db` next to the application binaries by default. Set `BOOKS_DATABASE` to choose another database path.

## Endpoints

- `GET /health` — health status
- `POST /books` — create a book; JSON fields: `title`, `author`, `year`, `isbn`
- `GET /books` — list all books; optionally filter with `?author=...`
- `GET /books/{id}` — retrieve a book
- `PUT /books/{id}` — replace a book's fields
- `DELETE /books/{id}` — delete a book

Title and author are required. Create returns `201`, successful reads and updates return `200`, successful deletion returns `204`, validation errors return `400`, and unknown IDs return `404`.

Example:

```sh
curl -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'http://localhost:5000/books?author=Frank%20Herbert'
```

## Tests

Run the offline test suite (no external NuGet packages required):

```sh
dotnet run --project BookCollection.Tests
```

The tests cover creating and reading books, filtering and updating, deletion, and persistence across repository instances.
