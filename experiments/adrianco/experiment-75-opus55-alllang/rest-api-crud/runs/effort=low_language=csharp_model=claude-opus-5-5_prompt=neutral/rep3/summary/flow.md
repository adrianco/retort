# Flow

```mermaid
sequenceDiagram
    Client->>Program.cs: POST /books {title, author, year, isbn}
    Program.cs->>BookInput: Validate()
    BookInput-->>Program.cs: [] (no errors)
    Program.cs->>BookRepository: Create(input)
    BookRepository->>SQLite: INSERT ... ; SELECT last_insert_rowid()
    SQLite-->>BookRepository: id
    BookRepository->>SQLite: SELECT ... WHERE id=$id
    SQLite-->>BookRepository: row
    BookRepository-->>Program.cs: Book
    Program.cs-->>Client: 201 Created {json}
```

A `POST /books` runs `BookInput.Validate()` (rejecting missing title/author and out-of-range year with a `400 {errors}`), then `BookRepository.Create` opens a fresh `SqliteConnection`, inserts via parameterized SQL, and re-reads the row to return the persisted `Book` with `201 Created` and a `Location` header. Each repository method opens and disposes its own connection; a shared in-memory connection is kept alive only for `Mode=Memory` connection strings (used by the tests). Input is parameterized throughout (no SQL injection); the author filter uses `COLLATE NOCASE` for case-insensitive matching.
