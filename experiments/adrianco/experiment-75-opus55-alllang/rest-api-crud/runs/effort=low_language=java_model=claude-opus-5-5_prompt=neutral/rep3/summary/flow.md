# Flow

```mermaid
sequenceDiagram
    Client->>App: POST /books {title, author, year, isbn}
    App->>App: parse() — JSON decode + validate title/author
    App->>BookRepository: create(Book)
    BookRepository->>SQLite: INSERT ... RETURN_GENERATED_KEYS
    SQLite-->>BookRepository: generated id
    BookRepository-->>App: Book(id, ...)
    App-->>Client: 201 {json Book}
```

A `POST /books` request is decoded by Jackson into a `Book` record and validated: a null/blank `title` or `author` short-circuits to `400 {errors:[...]}` before any DB access. On success `BookRepository.create` opens a fresh JDBC connection, inserts the row, reads the generated key, and returns the persisted `Book`, which `handle()` serializes to JSON with a `201`. Each repository method opens and closes its own connection and is `synchronized`; validation is limited to required-field presence (no ISBN/year format checks).
