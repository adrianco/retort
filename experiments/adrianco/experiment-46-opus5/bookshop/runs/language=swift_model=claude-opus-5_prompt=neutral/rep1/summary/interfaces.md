# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status,database}` / `503` | `HealthController.health` |
| GET | /books | `200 [BookResponse]` | `BookController.index` |
| GET | /books?author= | `200 [BookResponse]` (case-insensitive partial filter) | `BookController.index` |
| POST | /books | `201 BookResponse` + `Location` header / `400` | `BookController.create` |
| GET | /books/{id} | `200 BookResponse` / `404` / `400` (bad UUID) | `BookController.show` |
| PUT | /books/{id} | `200 BookResponse` / `404` / `400` | `BookController.update` |
| DELETE | /books/{id} | `204 No Content` / `404` / `400` | `BookController.delete` |

## Data schema

`books` table: `id` (UUID, pk), `title` (string, required), `author` (string, required), `year` (int, optional), `isbn` (string, optional), `created_at` (datetime), `updated_at` (datetime).

## Request/response DTOs

- `BookRequest` — all fields optional at decode time; `validated(now:)` enforces required title/author, year range (1000..next year), and ISBN-10/13 shape.
- `BookResponse` — always encodes every key (explicit `null` for absent optionals); ISO-8601 dates.
