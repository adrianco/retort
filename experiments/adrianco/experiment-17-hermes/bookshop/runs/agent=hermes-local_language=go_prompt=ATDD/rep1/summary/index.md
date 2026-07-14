# Summary: agent=hermes-local language=go prompt=ATDD · rep 1

- **Shape:** Go REST CRUD API using gorilla/mux + mattn/go-sqlite3, persisting to a `./books.db` SQLite file.
- **Structure:** 4 source modules (main, database, router, handlers), 2 test files.
- **Interfaces:** 6 HTTP routes (5 CRUD + `/health`), no CLI, no exported library API.
- **Notable:** Clean, idiomatic split of concerns for a small service; but tests share one on-disk DB with no reset (violates the ATDD "empty service per scenario" instruction), and `PUT`/`DELETE`/`GET-by-id` error handling is uneven (PUT on a missing id returns 500, not 404).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
