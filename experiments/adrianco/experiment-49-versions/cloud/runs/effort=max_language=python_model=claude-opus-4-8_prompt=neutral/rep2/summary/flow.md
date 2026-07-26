# Flow

```mermaid
sequenceDiagram
    Client->>app.py: POST /books {title, author, year, isbn}
    app.py->>app.py: validate_book(data)
    alt invalid
        app.py-->>Client: 400 {errors}
    else valid
        app.py->>get_db: sqlite3 connection (per-request g.db)
        get_db-->>app.py: Connection
        app.py->>books: INSERT ... ; SELECT lastrowid
        books-->>app.py: row
        app.py-->>Client: 201 {book} + Location header
    end
```

A `POST /books` request is validated (`title`/`author` required, non-empty; `year` int; `isbn` str) before touching the DB. On success it inserts the row into the request-scoped SQLite connection, re-reads it, and returns 201 with a `Location` header. Connections are opened lazily per request via `get_db()` and closed on Flask teardown. The app uses the application-factory pattern (`create_app`) so tests bind to an isolated `tmp_path` database.
