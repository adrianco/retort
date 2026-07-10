# Flow

```mermaid
sequenceDiagram
    Client->>app.py: POST /books {title, author, year, isbn}
    app.py->>app.py: validate title/author non-empty, coerce year
    app.py->>Book: Book(...); db.session.add + commit
    Book-->>app.py: persisted row (id assigned)
    app.py-->>Client: 201 {book json}
```

A `POST /books` request parses the JSON body, rejects it with 400 if the body is
missing or `title`/`author` are empty, coerces `year` to int (400 on failure),
then constructs a `Book`, commits it via SQLAlchemy to the SQLite `books.db`, and
returns the serialized book with 201. Validation is present for required fields
and year type. Note: string fields are `.strip()`-ed without a type check, so a
non-string `title`/`author` value (e.g. numeric JSON) raises `AttributeError`
and yields a 500 rather than a 400.
