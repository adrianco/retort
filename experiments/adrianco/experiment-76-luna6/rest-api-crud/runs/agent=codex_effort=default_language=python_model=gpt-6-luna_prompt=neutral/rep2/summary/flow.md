# Flow

```mermaid
sequenceDiagram
    Client->>app.py: POST /books {title, author, ...}
    app.py->>read_book: parse + validate JSON body
    read_book-->>app.py: {title, author, year, isbn}
    app.py->>SQLite: connect() (CREATE TABLE IF NOT EXISTS)
    app.py->>SQLite: INSERT INTO books (...)
    SQLite-->>app.py: lastrowid
    app.py-->>Client: 201 {book} + Location: /books/{id}
```

A `POST /books` request is parsed and validated by `read_book`, which rejects a non-object body or a missing/blank `title` or `author` with a `ValueError` (mapped to 400). On success the handler opens a fresh SQLite connection per request (via `connect()`, which lazily creates the `books` table), inserts the row, and returns the created book with a `Location` header and 201. Each handler opens its own short-lived connection inside a `with` block; there is no connection pooling or migration layer. Validation covers required strings plus optional-type checks on `year` (int) and `isbn` (str).
