# Books REST API (Clojure)

Ring + Compojure + next.jdbc on SQLite.

## Run
```
clojure -M:run          # PORT (default 3000), DB_PATH (default books.db)
```

## Test
```
clojure -M:test
```

## Endpoints
- `GET /health`
- `POST /books` — JSON `{title, author, year?, isbn?}`; title/author required → 201 / 400
- `GET /books[?author=Name]`
- `GET /books/:id` → 200 / 404
- `PUT /books/:id` — full replacement, same validation → 200 / 400 / 404
- `DELETE /books/:id` → 204 / 404
