# Flow

```mermaid
sequenceDiagram
    Client->>Program.cs: POST /books {title, author, year, isbn}
    Program.cs->>BookValidator: Validate(request)
    BookValidator-->>Program.cs: errors (empty = valid)
    alt errors present
        Program.cs-->>Client: 400 problem+json {errors}
    else valid
        Program.cs->>BookRepository: Add(ToBook(0, request))
        BookRepository->>SQLite: INSERT ... ; last_insert_rowid()
        SQLite-->>BookRepository: new id
        BookRepository-->>Program.cs: Book with Id
        Program.cs-->>Client: 201 Created + Location /books/{id}
    end
```

A `POST /books` request is validated by `BookValidator.Validate`; on any field error the handler returns `400` with an `application/problem+json` body keyed by field. On success the request is mapped to a `Book` (trimmed text, normalised ISBN), inserted via a short-lived SQLite connection, and the row id is read back with `last_insert_rowid()`. The created book is returned `201` with a `Location` header. The repository opens a fresh connection per operation (no pooling held open); the ISBN is stored as bare digits even though the client may send a hyphenated form.
