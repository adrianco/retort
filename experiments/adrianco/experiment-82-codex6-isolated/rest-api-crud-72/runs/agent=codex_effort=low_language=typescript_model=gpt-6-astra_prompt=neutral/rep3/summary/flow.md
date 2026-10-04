# Flow

```mermaid
sequenceDiagram
    Client->>app.ts: POST /books {title,author,year,isbn}
    app.ts->>app.ts: express.json() parse (limit 100kb)
    app.ts->>app.ts: validateBook(req.body)
    alt invalid
        app.ts-->>Client: 400 {error}
    else valid
        app.ts->>SQLite: INSERT ... RETURNING lastInsertRowid
        SQLite-->>app.ts: rowid
        app.ts-->>Client: 201 {id,...book} + Location
    end
```

A `POST /books` request is JSON-parsed (bodies over 100 KB rejected with 413), then `validateBook` enforces non-blank string `title`/`author` and optional-type checks on `year` (safe integer or null) and `isbn` (non-blank string or null), trimming strings. On success a parameterized `INSERT` persists the row to SQLite and the handler returns `201` with the created book and a `Location` header. Notable: input validation is present and thorough; SQL injection is avoided via prepared statements; ids are validated by an `app.param` guard; a terminal error middleware maps thrown errors to 400/413/500; PUT is a full replace (omitted optional fields become null).
