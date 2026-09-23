# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:ok}` | `App.java:20` |
| POST | /books | `201 Book \| 400 {errors}` | `App.java:40` → `BookRepository.create` |
| GET | /books | `200 [Book]` (optional `?author=` exact filter) | `App.java:39` → `BookRepository.list` |
| GET | /books/{id} | `200 Book \| 404` | `App.java:52` → `BookRepository.get` |
| PUT | /books/{id} | `200 Book \| 400 \| 404` | `App.java:53` → `BookRepository.update` |
| DELETE | /books/{id} | `204 \| 404` | `App.java:57` → `BookRepository.delete` |

Unsupported methods on a known path return `405`; unhandled exceptions return `500`.

## Data schema

`books` table (SQLite): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).

## Library API

`BookRepository.Book` — record `(Long id, String title, String author, Integer year, String isbn)`.
