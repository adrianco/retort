# Interfaces

## HTTP routes (all handlers return hard-coded literals — no persistence)

| Method | Path | Declared behaviour | Actual behaviour |
|--------|------|--------------------|------------------|
| GET | /health | health status | returns JSON array `[{"status":"healthy"},200]`, HTTP 200 |
| POST | /books | create book | returns `[{"message":"..."},201]`, HTTP **200**; no validation, no persistence |
| GET | /books | list (with `?author=`) | returns one hard-coded book; **no** `?author=` filtering |
| GET | /books/{id} | get by id | echoes id into a hard-coded book; no lookup, no 404 |
| PUT | /books/{id} | update | returns `[{"message":"..."},200]`; no update |
| DELETE | /books/{id} | delete | returns `[{"message":"..."},200]`; no delete |

## Data schema

None. `sqlite3` imported but no connection, table, or query exists.
