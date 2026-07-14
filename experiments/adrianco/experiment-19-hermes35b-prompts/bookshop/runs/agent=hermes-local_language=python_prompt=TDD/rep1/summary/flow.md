# Flow

```mermaid
sequenceDiagram
    Client->>app.py: POST /books {title, author, year, isbn}
    app.py->>app.py: validate title & author (400 if missing)
    app.py->>get_db(): connection on g
    get_db()-->>app.py: sqlite3.Connection
    app.py->>SQLite: INSERT INTO books ...
    app.py->>SQLite: SELECT * WHERE id = lastrowid
    SQLite-->>app.py: Row
    app.py-->>Client: 201 {book json}
```

A `POST /books` request first validates that `title` and `author` are present
(returning 400 otherwise), obtains a per-request SQLite connection cached on
Flask's `g`, inserts the row, re-selects it by `lastrowid`, and returns the full
book as JSON with 201. Read/update/delete follow the same connection pattern.

Notable: connection is opened per request but there is no `teardown_appcontext`
close/commit hook, so connections on `g` are not explicitly closed. The DB path
is threaded through the process-global `os.environ['DATABASE_PATH']` rather than
Flask config. `PUT` assumes a JSON body (`request.get_json()` → `.get(...)`),
which would raise on a bodyless request.
