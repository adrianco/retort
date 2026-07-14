# Flow

```mermaid
sequenceDiagram
    Client->>app.py: POST /books {title, author, year, isbn}
    app.py->>app.py: request.get_json()
    app.py->>app.py: validate title & author non-empty
    alt missing title/author
        app.py-->>Client: 400 {error}
    else valid
        app.py->>SQLite: INSERT INTO books (...)
        SQLite-->>app.py: lastrowid
        app.py->>SQLite: SELECT * WHERE id = ?
        SQLite-->>app.py: Row
        app.py-->>Client: 201 {book json}
    end
```

A request to `POST /books` parses the JSON body, rejects it with 400 if `title`
or `author` is missing/blank (after stripping whitespace), then inserts the row
into the request-scoped SQLite connection (`get_db()` on Flask `g`, WAL mode),
re-selects the inserted row by `lastrowid`, and returns it as JSON with 201. The
connection is closed in a `teardown_appcontext` hook. Notable: string coercion
and whitespace-stripping on title/author; `?author=` list filter uses a
substring `LIKE %author%` match rather than exact equality.
