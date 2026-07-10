# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `main.rs:health` |
| POST | /books | `201 Book` / `400` | `main.rs:create_book` |
| GET | /books | `200 [Book]` (optional `?author=`) | `main.rs:list_books` |
| GET | /books/{id} | `200 Book` / `404` | `main.rs:get_book` |
| PUT | /books/{id} | `200 Book` / `400` / `404` | `main.rs:update_book` |
| DELETE | /books/{id} | `204` / `404` | `main.rs:delete_book` |

## Data schema

`books` table: `id` (INTEGER, PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).

## Library API (internal)

`Db` — `init(path)`, `insert()`, `find_by_id()`, `list(author_filter)`, `update()`, `delete()`. `Book`, `CreateBookRequest`, `UpdateBookRequest`, `ErrorResponse` serde structs.
