# Summary: language=python model=opus-4.8 prompt=bdd · rep 1

- **Shape:** FastAPI REST API with a hand-rolled SQLite persistence layer (no ORM).
- **Structure:** 2 source modules (`main.py`, `db.py`) + 1 test file (`test_books.py`, 12 tests).
- **Interfaces:** 6 HTTP routes (5 CRUD on `/books` + `/health`), 1 `books` SQLite table, 2 exported classes/factories.
- **Notable:** Clean app-factory + dependency-injection design lets tests swap in an in-memory DB; Pydantic `Field(min_length=1)` enforces required fields declaratively; BDD Given/When/Then tests with behaviour-named functions.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
