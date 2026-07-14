# Interfaces

## HTTP routes (all in `app.py`)

| Method | Path | Description | Success | Errors |
|--------|------|-------------|---------|--------|
| GET | `/health` | Health check | 200 `{status: healthy}` | — |
| POST | `/books` | Create book (title, author, year, isbn) | 201 book | 400 missing title/author, 400 dup ISBN, 500 |
| GET | `/books` | List books, optional `?author=` filter | 200 `[book]` | 500 |
| GET | `/books/<int:id>` | Get one book | 200 book | 404 not found, 500 |
| PUT | `/books/<int:id>` | Update book | 200 book | 400 missing title/author, 404, 400 dup ISBN, 500 |
| DELETE | `/books/<int:id>` | Delete book | 200 `{message}` | 404 not found, 500 |

## Data schema

`books` table (SQLite): `id` INTEGER PK AUTOINCREMENT, `title` TEXT NOT NULL,
`author` TEXT NOT NULL, `year` INTEGER, `isbn` TEXT UNIQUE.
