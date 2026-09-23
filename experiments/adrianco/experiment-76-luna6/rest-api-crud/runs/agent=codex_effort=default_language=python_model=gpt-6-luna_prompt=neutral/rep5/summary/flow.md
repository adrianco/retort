# Flow

```mermaid
sequenceDiagram
    Client->>app.py: POST /books {title, author, year, isbn}
    app.py->>app.py: read_json() + validate title/author
    app.py->>SQLite: _connect(database)
    app.py->>SQLite: INSERT INTO books (...)
    SQLite-->>app.py: lastrowid
    app.py->>SQLite: SELECT * WHERE id = lastrowid
    SQLite-->>app.py: Row
    app.py-->>Client: 201 {book json}
```

A `POST /books` request reads and JSON-parses the body (`read_json`), rejecting a non-object body or a missing/blank `title` or `author` with `400`. On success it opens a fresh SQLite connection per request via `_connect` (which also lazily creates the `books` table), inserts the row, re-selects it by `lastrowid`, and returns `201` with the serialized book. Notable: a new SQLite connection is opened per request rather than reused; the `?author=` filter is exact-match only; there is no pagination.
