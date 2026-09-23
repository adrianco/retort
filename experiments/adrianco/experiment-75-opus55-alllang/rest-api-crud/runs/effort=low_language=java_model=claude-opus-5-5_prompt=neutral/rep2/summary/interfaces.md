# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `App.java:21` |
| POST | /books | `201 Book` / `400 {errors}` | `App.java:38` → `BookRepository.create` |
| GET | /books | `200 [Book]` (optional `?author=` exact match) | `App.java:37` → `BookRepository.list` |
| GET | /books/{id} | `200 Book` / `404` | `App.java:49` → `BookRepository.find` |
| PUT | /books/{id} | `200 Book` / `400` / `404` | `App.java:50` → `BookRepository.update` |
| DELETE | /books/{id} | `204` / `404` | `App.java:55` → `BookRepository.delete` |

Unsupported methods on a known path return `405`; unhandled exceptions return `500`. All non-empty bodies are `application/json`.

## Data schema

`books` table (`BookRepository.java:12`): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).

## Library API

`App` and `BookRepository` are constructible directly (used by tests): `new App(port, jdbcUrl)` with `port=0` binds an ephemeral port.
