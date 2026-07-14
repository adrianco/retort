# Flow

```mermaid
sequenceDiagram
    Client->>app.py: POST /books {title, author, year, isbn}
    app.py->>app.py: validate title/author non-empty
    app.py->>get_db: connection (g or shared :memory:)
    get_db-->>app.py: sqlite3.Connection
    app.py->>books.db: INSERT INTO books (...)
    books.db-->>app.py: cursor.lastrowid
    app.py-->>Client: 201 {id, title, author, year, isbn}
```

A `POST /books` request parses JSON, rejects missing/blank `title` or `author` with 400, then obtains a SQLite connection via `get_db()` (a per-request connection stored on Flask's `g` for file-based DBs, or a single shared connection for `':memory:'`). It inserts the row, commits, and returns the created book with its generated id at 201. Author filtering on `GET /books` uses `LIKE '%author%'` (substring match). No pagination.
