# Flow

```mermaid
sequenceDiagram
    Client->>app.py: POST /books {title, author, year, isbn}
    app.py->>app.py: read_book() validate Content-Type, size, fields
    app.py->>SQLite: INSERT INTO books(...)
    SQLite-->>app.py: lastrowid
    app.py->>SQLite: SELECT * FROM books WHERE id=?
    SQLite-->>app.py: row
    app.py-->>Client: 201 {book json} + Location
```

A `POST /books` first runs `read_book()`, which enforces `Content-Type: application/json`, a ≤1 MiB body, a JSON object with only the known fields, nonblank string `title`/`author`, and optional typed `year`/`isbn`. On success a fresh SQLite connection (opened per request via `connect()`, wrapped in `closing`) inserts the row inside a transaction, re-selects it, and returns `201` with a `Location` header. Errors are funneled through a single `APIError`/`sqlite3.Error` handler in `__call__` that emits JSON with the right status. Notable: parameterized SQL throughout (a SQL-injection filter case is explicitly tested); IDs handled as strings to avoid integer overflow; DELETE returns a bodyless 204; PUT is full-replace (omitted optional fields reset to null).
