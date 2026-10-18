# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status":"ok"}` | `main.rs:health` |
| POST | /books | `Book` → 201 / 400 | `main.rs:create_book` |
| GET | /books | `[Book]`, optional `?author=` exact-match filter → 200 | `main.rs:list_books` |
| GET | /books/:id | `Book` → 200 / 404 | `main.rs:get_book` |
| PUT | /books/:id | `Book` → 200 / 404 / 400 | `main.rs:update_book` |
| DELETE | /books/:id | 204 / 404 | `main.rs:delete_book` |

Routes use axum 0.7's `:id` path-parameter syntax, matching the pinned `axum = "0.7"`.

## Data schema

`books(id INTEGER PK AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT)`

## Error contract

`ApiError` → JSON `{"error": <msg>}` with 400 (validation), 404 (not found),
500 (database). Validation rejects empty/whitespace `title` or `author`.
