# Flow

```mermaid
sequenceDiagram
    Client->>app.ts: POST /books {title,author,year,isbn}
    app.ts->>validate.ts: validateBook(req.body)
    validate.ts-->>app.ts: {ok:true, value}
    app.ts->>db.ts: repo.create(value)
    db.ts->>sqlite: INSERT INTO books ...
    sqlite-->>db.ts: lastInsertRowid
    db.ts-->>app.ts: Book
    app.ts-->>Client: 201 {json Book}
```

A `POST /books` request is JSON-parsed by `express.json()`, then `validateBook` checks that `title` and `author` are non-empty strings and that `year`/`isbn` (if present) have the right type. On failure it returns 400 with an `errors[]` array. On success `BookRepository.create` runs a prepared `INSERT` against the `node:sqlite` database and re-reads the inserted row, which is returned as 201 JSON. Validation is centralized and reused by both POST and PUT; id parsing rejects non-positive/non-integer ids with 400; malformed JSON is handled by a dedicated error middleware.
