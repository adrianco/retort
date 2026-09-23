# Flow

```mermaid
sequenceDiagram
    Client->>app.ts: POST /books {title, author, year, isbn}
    app.ts->>app.ts: readJson(req) + validate(body)
    alt invalid
        app.ts-->>Client: 400 {errors}
    else valid
        app.ts->>books: INSERT (prepared stmt)
        books-->>app.ts: lastInsertRowid
        app.ts->>books: SELECT * WHERE id = ?
        books-->>app.ts: Book row
        app.ts-->>Client: 201 {book}
    end
```

A `POST /books` request is fully buffered by `readJson()` and parsed as JSON, then `validate()` trims and checks `title`/`author` (required) and the optional `year`/`isbn` types. On failure the handler returns `400` with an `errors` array; on success it inserts via a prepared statement, re-selects the row by `lastInsertRowid`, and returns it with `201`. All routes share one synchronous `node:sqlite` handle opened in `createApp()`. Notable: uses only Node built-ins (`node:http`, `node:sqlite`) with zero runtime dependencies; JSON parse errors are caught and mapped to `400`; the author filter is exact-match `COLLATE NOCASE` (not substring).
