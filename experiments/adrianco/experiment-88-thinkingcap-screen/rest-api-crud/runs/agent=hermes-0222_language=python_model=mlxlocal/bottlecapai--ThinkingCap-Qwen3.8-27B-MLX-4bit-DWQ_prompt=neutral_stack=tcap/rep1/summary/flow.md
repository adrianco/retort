# Flow

```mermaid
sequenceDiagram
    Client->>app.py: POST /books {title, author, year, isbn}
    app.py->>app.py: parse_book_payload(data)
    alt invalid payload
        app.py-->>Client: 400 {error}
    else valid
        app.py->>get_db: connection (per-request, g.db)
        get_db-->>app.py: sqlite3.Connection
        app.py->>books: INSERT ... ; SELECT lastrowid
        books-->>app.py: Row
        app.py-->>Client: 201 {book}
    end
```

A `POST /books` request is parsed and validated by `parse_book_payload` (title and author required non-empty strings; year must be int; isbn must be a non-empty string). On success a per-request SQLite connection from `get_db()` inserts the row, re-selects it by `lastrowid`, and returns it as JSON with 201. Validation rejects malformed input with 400 before touching the DB. Connections are opened lazily per request and closed via `teardown_appcontext`. Note: `init_db()` is invoked only under `__main__`, not inside `create_app()`, so a WSGI deployment of the module-level `app` would not auto-create the table.
