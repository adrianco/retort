# Flow

```mermaid
sequenceDiagram
    Client->>server.go: POST /books {json}
    server.go->>server.go: json.Decode(&Book)
    server.go->>models.go: book.Validate()
    models.go-->>server.go: nil (title+author present)
    server.go->>database.go: CreateBook(&book)
    database.go->>SQLite: INSERT INTO books ...
    SQLite-->>database.go: LastInsertId
    database.go-->>server.go: book.ID set
    server.go-->>Client: 201 {book json}
```

A `POST /books` request is decoded into a `Book`, validated (title and author
required — otherwise `400`), then inserted into the SQLite `books` table via
`database.go:CreateBook`, which back-fills the generated `ID`. The created book
is returned as JSON with `201 Created`. Error handling is consistent across
routes: decode failures and validation failures return `400`, missing rows
return `404`, and DB errors return `500`. `PUT` and `DELETE` explicitly
`GetBook` first to distinguish `404` from a successful mutation.
