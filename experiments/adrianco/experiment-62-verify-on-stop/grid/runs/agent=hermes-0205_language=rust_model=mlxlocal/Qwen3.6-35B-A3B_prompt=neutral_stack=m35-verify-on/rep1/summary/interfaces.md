# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:"healthy"}` | `main.rs:health_check` |
| POST | /books | `201 Book \| 400 {error}` | `main.rs:create_book` |
| GET | /books | `200 [Book]` (supports `?author=`) | `main.rs:list_books` |
| GET | /books/{id} | `200 Book \| 404 {error}` | `main.rs:get_book` |
| PUT | /books/{id} | `200 Book \| 404/400 {error}` | `main.rs:update_book` |
| DELETE | /books/{id} | `204 \| 404 {error}` | `main.rs:delete_book` |

## Data schema

`books` table (`models.rs:TABLE_DEF`): id (TEXT pk), title (TEXT not null), author (TEXT not null), year (INTEGER), isbn (TEXT), created_at (TEXT not null), updated_at (TEXT not null).

## Library API (internal)

`database.rs` exposes typed CRUD fns taking `&rusqlite::Connection`. `?author=` filter uses `LIKE '%author%'` (substring match). Validation lives in `create_book`/`update_book` (title/author required + non-empty).
