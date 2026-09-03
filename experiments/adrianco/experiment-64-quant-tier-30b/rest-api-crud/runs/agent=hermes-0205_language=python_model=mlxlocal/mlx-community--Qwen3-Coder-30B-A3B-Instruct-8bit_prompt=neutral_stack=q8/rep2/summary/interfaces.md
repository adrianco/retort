# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | `/health` | `200 {"status":"healthy"}` | `app.py:33 health_check` |
| POST | `/books` | `201 Book` \| `400` \| `500` | `app.py:38 create_book` |
| GET | `/books` (`?author=`) | `200 [Book]` | `app.py:80 get_books` |
| GET | `/books/<int:book_id>` | `200 Book` \| `404` | `app.py:109 get_book` |
| PUT | `/books/<int:book_id>` | `200 Book` \| `400` \| `404` \| `500` | `app.py:130 update_book` |
| DELETE | `/books/<int:book_id>` | `200 {"message":...}` \| `404` \| `500` | `app.py:179 delete_book` |

## CLI commands

(none — `python app.py` starts the dev server on `0.0.0.0:5001` with `debug=True`.)

## Library API

(none — no package, no `create_app()` factory; `app` is a module-level global.)

## Data schema

`books` table (SQLite, file `books.db`, created by `init_db()` at `app.py:10`):
`id` INTEGER PK AUTOINCREMENT, `title` TEXT NOT NULL, `author` TEXT NOT NULL,
`year` INTEGER, `isbn` TEXT.
