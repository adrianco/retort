# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status,database}` \| `503` | `HealthEndpoints.cs` |
| GET | /books | `200 [BookResponse]` (optional `?author=`) | `BookEndpoints.ListBooks` |
| GET | /books/{id} | `200 BookResponse` \| `404` | `BookEndpoints.GetBook` |
| POST | /books | `201 BookResponse` \| `400` \| `409` | `BookEndpoints.CreateBook` |
| PUT | /books/{id} | `200 BookResponse` \| `400` \| `404` \| `409` | `BookEndpoints.UpdateBook` |
| DELETE | /books/{id} | `204` \| `404` | `BookEndpoints.DeleteBook` |

Validation failures and not-found/conflict responses are RFC 7807 `ProblemDetails` JSON.

## Data schema

`Books` table: `Id` (int, pk, identity), `Title` (str, required, ≤500), `Author`
(str, required, ≤300, indexed), `Year` (int?, nullable), `Isbn` (str?, ≤13,
unique index, nullable), `CreatedAt` / `UpdatedAt` (DateTimeOffset).

## CLI commands

(none)

## Library API

(none — application project, not a library)
