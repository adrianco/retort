# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:ok}` | `BookController:health` |
| POST | /books | `201 Book` / `400` | `BookController:create` |
| GET | /books | `200 [Book]` (optional `?author=`) | `BookController:list` |
| GET | /books/{id} | `200 Book` / `404` | `BookController:get` |
| PUT | /books/{id} | `200 Book` / `404` / `400` | `BookController:update` |
| DELETE | /books/{id} | `204` / `404` | `BookController:delete` |

Errors are emitted as JSON `{"error": "..."}` by `GlobalExceptionHandler`
(400 for validation, malformed JSON, and non-numeric id; 404 via
`ResponseStatusException`).

## Data schema

`books` table (SQLite): `id` INTEGER PK AUTOINCREMENT, `title` TEXT NOT NULL,
`author` TEXT NOT NULL, `year` INTEGER (nullable), `isbn` TEXT (nullable).

## CLI commands

(none)

## Library API

(none — application service)
