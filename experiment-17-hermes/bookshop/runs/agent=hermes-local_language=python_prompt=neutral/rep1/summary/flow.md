# Flow

```mermaid
sequenceDiagram
    Client->>app.py: POST /books {title, author, year, isbn}
    app.py->>app.py: validate title & author present
    alt missing title/author
        app.py-->>Client: 400 {error}
    else valid
        app.py->>books.db: INSERT INTO books (...)
        books.db-->>app.py: lastrowid
        app.py-->>Client: 201 {id, title, author, year, isbn}
    end
```

A request to `POST /books` reads the JSON body, rejects it with `400` if `title` or
`author` is falsy, otherwise opens a fresh `sqlite3` connection via
`get_db_connection()`, inserts the row, and returns the created book with its new id
and `201`. Each handler opens and closes its own connection (no pooling). The
`?author=` filter on `GET /books` uses a `LIKE '%author%'` substring match rather than
an exact match. `debug=True` is set on `app.run`.
