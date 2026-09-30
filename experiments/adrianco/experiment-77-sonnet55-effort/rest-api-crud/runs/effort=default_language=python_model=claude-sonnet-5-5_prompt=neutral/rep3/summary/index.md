# Architecture Summary — rest-api-crud (python, claude-sonnet-5-5, rep3)

A single-file book-collection REST API built on the Python **standard library only**
(`http.server` + `sqlite3`), no third-party runtime dependencies.

## Modules

| File | Role |
|------|------|
| `app.py` | Everything: persistence (`Store`), validation (`validate`), HTTP routing (`Handler`), server factory (`make_server`), CLI entrypoint. |
| `test_app.py` | pytest integration suite — spins a real server on an ephemeral port and drives it over HTTP with `urllib`. |
| `README.md` | Setup, run, endpoint table, curl example, test instructions. |

## Interfaces / flow

- **`Store`** wraps a `sqlite3` connection (thread-safe via a `threading.Lock`,
  `check_same_thread=False`). CRUD methods: `create / get / list(author=None) /
  update / delete`. Table `books(id PK AUTOINCREMENT, title NOT NULL, author NOT NULL,
  year INTEGER, isbn TEXT)`.
- **`validate(data)`** → `(clean_book, errors)`. Requires non-empty `title`/`author`;
  type-checks optional `year` (int, rejects bool) and `isbn` (str).
- **`Handler._route(method)`** dispatches on path:
  - `GET /health` → `{"status":"ok"}`
  - `/books` → GET (list, `?author=` filter) / POST (create, 201)
  - `/books/{id}` (regex `^/books/(\d+)/?$`) → GET / PUT / DELETE, 404 when absent
  - unknown method → 405, unknown path → 404
- **`make_server(host, port, db_path)`** binds a per-server `Store` onto a subclass of
  `Handler` and returns a `ThreadingHTTPServer`. Tests pass `port=0` for an ephemeral
  port and the default `:memory:` DB; `__main__` uses `DB_PATH` (default file `books.db`).

## Notes

- Status codes: 201 create, 200 read/list/update, 204 delete, 404 not-found,
  400 malformed JSON, 422 validation failure, 405 method-not-allowed.
- Concurrency handled with a single mutex around all DB access; correct but serializes
  writes (acceptable for the task scope).
