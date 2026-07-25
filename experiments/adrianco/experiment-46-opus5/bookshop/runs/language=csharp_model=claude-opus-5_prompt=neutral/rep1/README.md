# Book Collection API

A REST API for managing a book collection, built with ASP.NET Core Minimal APIs and
Entity Framework Core over SQLite.

## Requirements

- [.NET SDK 10.0](https://dotnet.microsoft.com/download) or later

No other dependencies — SQLite is embedded, so there is no database server to install.

## Setup and run

```bash
dotnet restore
dotnet run --project src/BookApi
```

The API listens on <http://localhost:5239>. The schema is created automatically on
startup in `src/BookApi/books.db`.

Point it at a different database file with the `ConnectionStrings__Books` environment
variable:

```bash
ConnectionStrings__Books="Data Source=/var/data/books.db" dotnet run --project src/BookApi
```

## Tests

```bash
dotnet test
```

49 tests: unit tests for ISBN parsing and request validation, plus integration tests
that boot the real application with `WebApplicationFactory` and drive it over HTTP.
Each integration test gets its own throwaway SQLite file, so the tests are isolated and
order-independent, and they exercise the same storage engine used in production.

## API

| Method   | Route          | Description                             |
| -------- | -------------- | --------------------------------------- |
| `GET`    | `/health`      | Liveness check, including the database   |
| `POST`   | `/books`       | Create a book                            |
| `GET`    | `/books`       | List books, optionally `?author=` filter |
| `GET`    | `/books/{id}`  | Fetch one book                           |
| `PUT`    | `/books/{id}`  | Replace a book                           |
| `DELETE` | `/books/{id}`  | Delete a book                            |

### Book fields

| Field    | Type     | Required | Notes                                                      |
| -------- | -------- | -------- | ---------------------------------------------------------- |
| `title`  | string   | yes      | Trimmed; max 500 characters                                 |
| `author` | string   | yes      | Trimmed; max 300 characters                                 |
| `year`   | integer  | no       | Between 1450 and next year                                  |
| `isbn`   | string   | no       | Valid ISBN-10 or ISBN-13; must be unique across the library |

`id`, `createdAt` and `updatedAt` are set by the server and ignored if sent by a client.

Hyphens and spaces in an ISBN are accepted and stripped, so `978-0-441-01359-3` is
stored and returned as `9780441013593`. The check digit is verified, so a typo is
rejected rather than saved.

### Status codes

| Code  | When                                                              |
| ----- | ----------------------------------------------------------------- |
| `200` | Successful `GET` or `PUT`                                          |
| `201` | Book created; the `Location` header points at the new resource     |
| `204` | Book deleted                                                       |
| `400` | Validation failed, or the body was not valid JSON                  |
| `404` | No book with that id                                               |
| `409` | Another book already uses that ISBN                                |
| `503` | `/health` only — the database is unreachable                       |

Errors use [RFC 9457 problem details](https://www.rfc-editor.org/rfc/rfc9457). Validation
failures report every broken field at once rather than stopping at the first:

```json
{
  "type": "https://tools.ietf.org/html/rfc9110#section-15.5.1",
  "title": "One or more validation errors occurred.",
  "status": 400,
  "errors": {
    "Title": ["Title is required."],
    "Author": ["Author is required."]
  }
}
```

## Examples

```bash
# Health check
curl http://localhost:5239/health
# {"status":"healthy","database":"up"}

# Create
curl -X POST http://localhost:5239/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-01359-3"}'
# 201 Created, Location: /books/1

# List, and filter by author (partial, case-insensitive)
curl http://localhost:5239/books
curl 'http://localhost:5239/books?author=herbert'

# Fetch one
curl http://localhost:5239/books/1

# Replace
curl -X PUT http://localhost:5239/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

# Delete
curl -X DELETE http://localhost:5239/books/1
# 204 No Content
```

## Design notes

- **`PUT` replaces, it does not merge.** A field left out of the body is cleared, which
  is what `PUT` means in HTTP. The example above drops `isbn`, so the stored ISBN becomes
  `null`. Use a `PATCH` endpoint if partial updates are needed later.
- **`?author=` is a partial, case-insensitive match**, so `?author=herbert` finds
  "Frank Herbert". `%` and `_` in the filter are escaped and matched literally rather
  than acting as SQL wildcards.
- **ISBNs are unique**, since they identify an edition. Books without an ISBN are
  exempt — SQLite treats `NULL`s as distinct in a unique index, so any number of books
  may omit it. Uniqueness is enforced by a database index as well as an application
  check, so concurrent writers cannot slip a duplicate through the gap.
- **The health check queries the database** rather than just returning `200`. A health
  check that ignores its datastore can report healthy while every request fails.
- **The schema is created with `EnsureCreated` on startup.** That suits a small,
  single-table service; a longer-lived one should switch to EF Core migrations
  (`db.Database.MigrateAsync()`).

## Layout

```
src/BookApi/
  Program.cs                        # host, DI and startup
  Models/Book.cs                    # entity
  Data/BookDbContext.cs             # EF Core mapping, indexes
  Contracts/Contracts.cs            # request and response shapes
  Validation/BookRequestValidator.cs
  Validation/Isbn.cs                # ISBN-10/13 check-digit verification
  Endpoints/BookEndpoints.cs        # /books
  Endpoints/HealthEndpoints.cs      # /health
tests/BookApi.Tests/
  BookApiFactory.cs                 # boots the app against a temp SQLite file
  BooksEndpointTests.cs             # HTTP integration tests
  BookRequestValidatorTests.cs
  IsbnTests.cs
```
