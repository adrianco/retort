# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | `/health` | `{"status":"healthy"}` 200 | `app.py:33 health_check` |
| POST | `/books` | `Book` 201 \| 400 \| 500 | `app.py:38 create_book` |
| GET | `/books` | `[Book]` 200 (optional `?author=` LIKE filter) | `app.py:72 get_books` |
| GET | `/books/<int:book_id>` | `Book` 200 \| 404 | `app.py:86 get_book` |
| PUT | `/books/<int:book_id>` | `Book` 200 \| 400 \| 404 \| 500 | `app.py:98 update_book` |
| DELETE | `/books/<int:book_id>` | `{"message":...}` 200 \| 404 \| 500 | `app.py:137 delete_book` |

## CLI commands

(none) — `python app.py` starts the dev server on `0.0.0.0:5001` with `debug=True`.

## Library API

(none exported for reuse; `app` and `init_db` are imported by `test_app.py`.)

## Data schema

`books` table (`app.py:10 init_db`), SQLite file `books.db`:
`id` INTEGER PRIMARY KEY AUTOINCREMENT, `title` TEXT NOT NULL, `author` TEXT NOT NULL,
`year` INTEGER, `isbn` TEXT.
