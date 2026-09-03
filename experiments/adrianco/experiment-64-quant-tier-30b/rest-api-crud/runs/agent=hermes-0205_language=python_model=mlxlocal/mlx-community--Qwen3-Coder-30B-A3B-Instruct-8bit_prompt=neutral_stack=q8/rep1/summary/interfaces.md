# Interfaces

## HTTP routes

| Method | Path | Description | Codes |
|--------|------|-------------|-------|
| GET | `/health` | Liveness probe, returns `{"status": "healthy"}` | 200 |
| POST | `/books` | Create a book from `title`, `author`, `year`, `isbn` | 201, 400, 500 |
| GET | `/books` | List books; optional `?author=` substring filter (`LIKE %v%`) | 200 |
| GET | `/books/<int:book_id>` | Fetch one book | 200, 404 |
| PUT | `/books/<int:book_id>` | Full replace of a book | 200, 400, 404, 500 |
| DELETE | `/books/<int:book_id>` | Remove a book | 200, 404, 500 |

All responses are JSON via `flask.jsonify`.

## Data schema

SQLite file `books.db` (module-level constant `DATABASE` in `app.py:6`):

```sql
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT
)
```

`sqlite3.Row` row factory; every query uses bound parameters (no string interpolation into SQL).

## Library API

None — `app.py` is a script module. `init_db()` is called only under `if __name__ == '__main__'` (`app.py:196`) and directly by the test fixture.
