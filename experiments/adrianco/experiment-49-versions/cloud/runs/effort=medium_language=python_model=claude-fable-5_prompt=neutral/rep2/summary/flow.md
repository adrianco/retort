# Flow

```mermaid
sequenceDiagram
    Client->>app.py: POST /books {title, author, year, isbn}
    app.py->>app.py: request.get_json(silent=True)
    app.py->>app.py: validate_payload(data)
    app.py->>SQLite: INSERT INTO books (...)
    SQLite-->>app.py: lastrowid
    app.py->>SQLite: SELECT * FROM books WHERE id=?
    SQLite-->>app.py: row
    app.py-->>Client: 201 {book json}
```

A `POST /books` parses the JSON body (400 on invalid JSON), runs
`validate_payload` which requires non-empty string `title` and `author` and
type-checks optional `year`/`isbn` (400 on error), inserts the row into SQLite,
then re-selects and returns the created book as JSON with 201. Each request gets
a per-request SQLite connection stored on Flask's `g` and closed on teardown.
Validation, error handling, and correct status codes are all present.
