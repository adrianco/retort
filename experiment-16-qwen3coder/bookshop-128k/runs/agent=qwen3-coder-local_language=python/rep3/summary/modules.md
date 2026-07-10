# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask HTTP server, SQLite access, all route handlers | `app`, `init_db()`, `get_db_connection()`, 7 route fns |
| test_app.py | unittest integration tests via Flask test client | `BookAPITestCase` (11 test methods) |
| requirements.txt | Dependency pin | `Flask==2.3.3` |
| README.md | Setup / run / usage docs | — |
| start.sh | Launch helper | — |
