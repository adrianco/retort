# Architecture Summary

Single-module Flask REST API for a book collection, backed by SQLite.

## Modules

- **`app.py`** (184 LOC) — the entire service.
  - `init_db()` — creates the `books` table (`id` PK autoincrement, `title`/`author` NOT NULL, `year`, `isbn` UNIQUE).
  - `get_db_connection()` — opens a `sqlite3` connection with `Row` factory (dict-like rows).
  - Routes:
    - `GET /health` → `{"status": "healthy"}` (200)
    - `POST /books` → validates `title`+`author`, inserts, returns created book (201); 400 on missing fields / duplicate ISBN; 500 on error
    - `GET /books` → lists all, optional `?author=` LIKE filter, ordered by title (200)
    - `GET /books/<int:id>` → single book (200) or 404
    - `PUT /books/<int:id>` → validates + updates, returns updated book (200) or 404
    - `DELETE /books/<int:id>` → removes book (200) or 404
  - Entrypoint runs `init_db()` then serves on `0.0.0.0:5001` (debug).
- **`test_app.py`** (239 LOC) — `unittest` suite, 11 test methods using Flask's `test_client`; `setUp`/`tearDown` init and delete the shared `books.db`.

## Interfaces / Data Flow

Client → Flask route → per-request `sqlite3` connection → `books.db` on disk → JSON response. No service/repository layer — routes talk to SQLite directly. Connections are opened and closed per request.

## Notes

- Persistence is a file DB (`books.db`); tests exercise the same filename and clean it up between cases.
- No dependency manifest; Flask is assumed present in the environment.
