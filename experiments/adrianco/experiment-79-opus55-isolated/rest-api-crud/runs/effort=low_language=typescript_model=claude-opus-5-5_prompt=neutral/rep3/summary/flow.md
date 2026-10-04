# Flow

```mermaid
sequenceDiagram
    Client->>app.ts: POST /books {title,author,...}
    app.ts->>app.ts: readJson() (1MB guard)
    app.ts->>validation.ts: validateBook(body)
    validation.ts-->>app.ts: {ok:true, value}
    app.ts->>store.ts: create(input)
    store.ts->>sqlite: INSERT ... RETURNING
    sqlite-->>store.ts: row
    store.ts-->>app.ts: Book
    app.ts-->>Client: 201 {json} + Location header
```

A `POST /books` request is read with a 1 MB body cap, JSON-parsed (400 on malformed JSON), and passed to `validateBook`, which enforces required `title`/`author` and typed optional `year`/`isbn`. On success `BookStore.create` runs a parameterized `INSERT ... RETURNING` against `node:sqlite` and the new book is returned with a `201` and a `Location` header. Errors flow through a single `HttpError`-aware `.catch` that maps known errors to their status codes and unknown errors to 500. Input validation, error handling, and parameterized queries are all present.
