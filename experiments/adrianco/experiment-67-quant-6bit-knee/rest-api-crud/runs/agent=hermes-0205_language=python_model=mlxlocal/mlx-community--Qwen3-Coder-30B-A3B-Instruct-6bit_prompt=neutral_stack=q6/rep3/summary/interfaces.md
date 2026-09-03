# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | `/health` | `{"status":"healthy"}` · 200 | `app.py:33 health_check` |
| POST | `/books` | created `Book` · 201, or `{"error":…}` · 400 | `app.py:38 create_book` |
| GET | `/books` | `[Book]` · 200 (optional `?author=` substring filter) | `app.py:72 get_books` |
| GET | `/books/<int:book_id>` | `Book` · 200, or `{"error":…}` · 404 | `app.py:88 get_book` |
| PUT | `/books/<int:book_id>` | updated `Book` · 200, 400 on missing fields, 404 if absent | `app.py:101 update_book` |
| DELETE | `/books/<int:book_id>` | `{"message":…}` · 200, or 404 | `app.py:141 delete_book` |

## CLI commands

(none) — `python app.py` starts the dev server on `0.0.0.0:5000`.

## Library API

(none exported for reuse; `app`, `init_db` are imported by the tests.)

## Data schema

`books` table (SQLite, file `books.db`, created by `app.py:10 init_db`):
`id` INTEGER PRIMARY KEY AUTOINCREMENT, `title` TEXT NOT NULL, `author` TEXT NOT NULL,
`year` INTEGER, `isbn` TEXT.
