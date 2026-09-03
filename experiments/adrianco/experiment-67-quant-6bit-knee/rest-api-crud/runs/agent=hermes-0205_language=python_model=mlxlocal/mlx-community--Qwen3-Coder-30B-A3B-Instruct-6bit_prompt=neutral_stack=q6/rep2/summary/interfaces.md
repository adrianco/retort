# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | `/health` | `200 {"status":"healthy"}` | `app.py:36 health_check` |
| POST | `/books` | `201 Book` \| `400` \| `500` | `app.py:41 create_book` |
| GET | `/books` | `200 [Book]` (optional `?author=`) | `app.py:83 get_books` |
| GET | `/books/<int:book_id>` | `200 Book` \| `404` | `app.py:112 get_book` |
| PUT | `/books/<int:book_id>` | `200 Book` \| `400` \| `404` \| `500` | `app.py:133 update_book` |
| DELETE | `/books/<int:book_id>` | `200 {"message":...}` \| `404` \| `500` | `app.py:183 delete_book` |

`Book` is serialised inline in each handler as
`{id, title, author, year, isbn}` — there is no shared serialiser.

## CLI commands

(none) — `python app.py` runs the dev server on `0.0.0.0:5000` with `debug=True` (`app.py:208`).

## Library API

(none exported deliberately; `test_app.py` imports `app` and `init_db` directly.)

## Data schema

`books` table (`app.py:16-24`), created with `CREATE TABLE IF NOT EXISTS`:

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT |
| `title` | TEXT | NOT NULL |
| `author` | TEXT | NOT NULL |
| `year` | INTEGER | — |
| `isbn` | TEXT | — |

Database file path: `os.path.abspath(os.environ.get('DATABASE', 'books.db'))`,
resolved **once at import time** (`app.py:8`).
