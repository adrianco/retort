# Flow

```mermaid
sequenceDiagram
    Client->>index.ts: POST /books {title,author,year,isbn}
    index.ts->>index.ts: validateBook(body)
    index.ts->>SQLite: INSERT INTO books (...)
    SQLite-->>index.ts: lastID
    index.ts->>SQLite: SELECT * FROM books WHERE id=?
    SQLite-->>index.ts: row
    index.ts-->>Client: 201 {book json}
```

A `POST /books` request is validated (`title` and `author` required, else 400), inserted into
the in-memory SQLite table, then re-selected by `lastID` and returned as JSON with 201. All
handlers use the callback-based `sqlite3` driver directly. Persistence is in-memory only, so
data does not survive a restart. No pagination on the list route; `?author=` filters via an
exact-match SQL WHERE clause.
