# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | `/health` | `{"status": "healthy"}` (200) | `main.py:53 health_check` |
| POST | `/books` | `Book` (200; 422 on missing `title`/`author`) | `main.py:58 create_book` |
| GET | `/books` | `[Book]` (200); optional `?author=` substring filter | `main.py:76 get_books` |
| GET | `/books/{book_id}` | `Book` (200) \| 404 `{"detail": "Book not found"}` | `main.py:103 get_book` |
| PUT | `/books/{book_id}` | `Book` (200) \| 404 \| 400 (empty patch) | `main.py:123 update_book` |
| DELETE | `/books/{book_id}` | `{"message": "Book deleted successfully"}` (200) \| 404 | `main.py:180 delete_book` |

## CLI commands

`python main.py` runs `uvicorn.run(app, host="0.0.0.0", port=8000)` (`main.py:197-199`). No argument parsing.

## Library API

Pydantic models exported from `main`: `Book` (id, title, author, year, isbn — id/year/isbn optional), `BookCreate` (title, author required; year, isbn optional), `BookUpdate` (all four optional). Plus `init_db()`.

## Data schema

`books` table in SQLite file `books.db` (`main.py:35-43`):
`id` INTEGER PRIMARY KEY AUTOINCREMENT, `title` TEXT NOT NULL, `author` TEXT NOT NULL, `year` INTEGER, `isbn` TEXT.
