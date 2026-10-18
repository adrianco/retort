# Flow

```mermaid
sequenceDiagram
    Client->>Routes.swift: POST /books {json}
    Routes.swift->>Routes.swift: request.decode(BookInput)
    Routes.swift->>BookValidator: validate(input)
    BookValidator-->>Routes.swift: BookDraft (or 400 ValidationError)
    Routes.swift->>BookStore: await create(draft)
    BookStore->>CSQLite: INSERT INTO books ...
    CSQLite-->>BookStore: last_insert_rowid
    BookStore-->>Routes.swift: Book
    Routes.swift-->>Client: 201 {json Book}
```

A `POST /books` decodes the JSON body into `BookInput` (malformed JSON → 400), validates it via `BookValidator` (missing title/author, out-of-range year, or malformed ISBN → 400 with a `details` list of every problem), then persists it through the `BookStore` actor, which binds a prepared `INSERT` against SQLite via the `CSQLite` system-library shim and returns the row with its generated id. All DB access is serialized through the actor. Validation is thorough (trimming, year range 1000..next-year, ISBN-10/13 shape check) and exceeds the spec's "title and author required" minimum.
