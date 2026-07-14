# Flow

```mermaid
sequenceDiagram
    Client->>app.ts: POST /books {title, author, year, isbn}
    app.ts->>books.ts: route /books
    books.ts->>validation.ts: validateBookCreate
    validation.ts->>Book.ts: validateBookInput(body)
    Book.ts-->>validation.ts: {valid, errors}
    alt invalid
        validation.ts-->>Client: 400 {error, details}
    else valid
        validation.ts->>BookController.ts: next()
        BookController.ts->>BookRepository.ts: create(body)
        BookRepository.ts->>Database.ts: create(book)
        Database.ts-->>BookRepository.ts: BookRow (new id, timestamps)
        BookRepository.ts-->>BookController.ts: Book
        BookController.ts-->>Client: 201 {json}
    end
```

A `POST /books` request is JSON-parsed, then run through `validateBookCreate` middleware which delegates to the model's `validateBookInput`. On failure it returns `400` with a details array. On success, `BookController.create` calls `bookRepository.create`, which delegates to the in-memory `DatabaseManager.create`; the store assigns an auto-incremented `id` (max existing id + 1), stamps `createdAt`/`updatedAt`, pushes to an in-memory array, and returns the new record with `201`.

Deviations from common patterns: storage is a plain in-memory JS array, not SQLite (task asked for SQLite or embedded-DB equivalent); persistence is optional JSON-file writes gated on a non-`:memory:` `DB_PATH`. The author filter is exact-match, not substring. All DB operations are synchronous. The `create` handler is not wrapped in try/catch, relying on the global error middleware for unexpected failures.
