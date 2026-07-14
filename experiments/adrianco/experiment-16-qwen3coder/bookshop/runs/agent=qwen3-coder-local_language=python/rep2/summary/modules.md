# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask HTTP server, Book model, route handlers | `app`, `db`, `Book`, `create_book`, `get_books`, `get_book`, `update_book`, `delete_book`, `health_check` |
| test_app.py | unittest API integration tests against Flask test client | `BookAPITestCase` (11 test methods) |
| integration_test.py | End-to-end test that launches `app.py` and hits it over HTTP | `run_app`, `test_api` |
| verify.py | Import/structure sanity check | `test_imports`, `test_structure` |
| README.md | Setup, run, and usage documentation | (docs) |
