# Flow

```mermaid
sequenceDiagram
    Client->>app.ts: POST /books {title,author,year,isbn}
    app.ts->>app.ts: express.json() parse (100kb limit)
    app.ts->>app.ts: validate(body)
    alt invalid
        app.ts-->>Client: 400 {error}
    else valid
        app.ts->>SQLite: INSERT INTO books (...)
        SQLite-->>app.ts: lastInsertRowid
        app.ts->>SQLite: SELECT * WHERE id = ?
        SQLite-->>app.ts: created row
        app.ts-->>Client: 201 {book} + Location header
    end
```

A `POST /books` request is JSON-parsed (bodies over 100 KB rejected with 413), then `validate()` requires non-empty `title` and `author` strings and type-checks optional `year`/`isbn`, throwing→400 on any failure. On success the row is inserted with bound parameters, re-selected by `lastInsertRowid`, and returned as 201 with a `Location: /books/{id}` header. All SQL uses bound parameters (verified by the author-filter test issuing `' OR 1=1 --` as data). Persistence is on-disk SQLite via `node:sqlite`, so data survives process restart (covered by the reopen test).
