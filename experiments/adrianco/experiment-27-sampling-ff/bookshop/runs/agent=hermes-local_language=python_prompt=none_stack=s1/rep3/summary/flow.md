# Flow

```mermaid
sequenceDiagram
    Client->>app.py: POST /books {title, author, year, isbn}
    app.py->>app.py: validate title/author (400 if missing)
    app.py->>SQLite: INSERT INTO books
    SQLite-->>app.py: lastrowid
    app.py->>SQLite: SELECT * WHERE id = ?
    SQLite-->>app.py: row
    app.py-->>Client: 201 {book json}
```

A `POST /books` parses the JSON body, rejects missing/blank `title` or `author` with 400, coerces `year` to int (400 on failure), inserts the row into SQLite via a per-request connection (`get_db()` stored on Flask `g`, closed at teardown), then re-selects the inserted row and returns it as JSON with 201. Input validation is present; the author filter uses a `LIKE %...%` substring match. No pagination, no auth.
