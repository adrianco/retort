# Flow

```mermaid
sequenceDiagram
    Client->>app.py: POST /books {title, author, year, isbn}
    app.py->>app.py: normalize(body_json()) validate title/author
    app.py->>SQLite: INSERT INTO books(...)
    SQLite-->>app.py: lastrowid
    app.py->>SQLite: SELECT * FROM books WHERE id=?
    SQLite-->>app.py: row
    app.py-->>Client: 201 {json book}
```

A `POST /books` request reads the JSON body (`body_json`), validates that `title` and `author` are non-empty strings and that `year`/`isbn` have the right types (`normalize`); on failure it returns `400`. On success it opens a fresh SQLite connection per request (`connect`), inserts the row, re-selects it by `lastrowid`, and returns `201` with the created book as JSON. Each handler method opens its own short-lived connection (no shared pool). Route-to-id parsing is done by a static `book_id()` helper that only accepts numeric ids. The `?author=` filter uses a `LIKE '%…%' COLLATE NOCASE` substring match rather than exact equality.
