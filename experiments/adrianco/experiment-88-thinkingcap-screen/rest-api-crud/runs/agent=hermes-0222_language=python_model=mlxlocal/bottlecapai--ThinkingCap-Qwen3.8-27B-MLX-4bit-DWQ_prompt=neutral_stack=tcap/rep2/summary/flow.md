# Flow

```mermaid
sequenceDiagram
    Client->>app.py: POST /books {title, author, year, isbn}
    app.py->>app.py: _string_field() validate title/author (required)
    app.py->>app.py: _year_is_valid()/_parse_year() validate year
    app.py->>get_db(): per-request sqlite3 connection (g.db)
    get_db()-->>app.py: Connection (row_factory=Row)
    app.py->>SQLite: INSERT INTO books ...; SELECT by lastrowid
    SQLite-->>app.py: row
    app.py-->>Client: 201 {id, title, author, year, isbn}
```

A `POST /books` request is parsed with `request.get_json(silent=True)`; a non-object body returns 400. `title` and `author` are validated as required non-empty strings, `year` is validated as int/digit-string/null, and `isbn` is an optional string. The row is inserted via a per-request SQLite connection (opened lazily in `get_db()`, closed in `teardown_appcontext`), re-selected, and returned as JSON with 201. The same validation helpers back the partial-update path in `PUT /books/{id}`. Input validation, correct status codes, and 404 handling for by-id/update/delete are all present.
