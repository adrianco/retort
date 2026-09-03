# Summary: stack=q4 prompt=neutral · rep 5

- **Shape:** FastAPI + SQLite CRUD, but split into two disconnected halves — a served app
  (`main.py`, 2 routes) and an unrouted function library (`book_api.py`, full CRUD).
- **Structure:** 3 source modules + 1 debug script, 3 test files (only 2 are real, assertionless smoke scripts).
- **Interfaces:** 2 served HTTP routes (`/health`, `GET /books`) out of the 6 required; 6 CRUD functions defined but never wired to routes.
- **Notable:** The full CRUD logic exists but is never imported by the app. The HTTP
  integration test (`test_book_api.py`) targets endpoints the served app does not implement
  and starts a uvicorn subprocess at import time.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
