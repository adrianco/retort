# Flow

```mermaid
sequenceDiagram
    Client->>index.ts: POST /books {title,author,year,isbn}
    index.ts->>middleware.ts: parseBody (manual JSON parse)
    middleware.ts-->>routes.ts: req.body
    routes.ts->>middleware.ts: validateBook(input)
    middleware.ts-->>routes.ts: errors[]
    routes.ts->>database.ts: getDb().prepare(INSERT).run(...)
    database.ts-->>routes.ts: lastInsertRowid
    routes.ts->>database.ts: SELECT * WHERE id=?
    database.ts-->>routes.ts: Book row
    routes.ts-->>Client: 201 {Book}
```

A `POST /books` request is body-parsed by the custom `parseBody` middleware (which hand-parses JSON off the raw request stream rather than using `express.json()`), validated by `validateBook`, inserted via a prepared `better-sqlite3` statement, re-read by id, and returned as `201`. A `SQLITE_CONSTRAINT_UNIQUE` on the isbn column is caught and mapped to `409`. Not-found and validation errors are thrown as plain tagged objects (`{type:'not_found'}`) and converted to `404`/`400` by the `handleError` error middleware. Validation requires all four fields (title, author, year, isbn) on create, which is stricter than the spec (which only mandates title and author).
