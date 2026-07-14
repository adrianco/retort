# Summary: agent=hermes-local language=python prompt=none stack=s8 · rep 3

- **Shape:** Flask REST API with raw `sqlite3` persistence via an application-factory pattern.
- **Structure:** 2 modules (app.py, test_app.py), 1 test file.
- **Interfaces:** 6 HTTP routes, 0 CLI commands, 1 exported factory (`create_app`).
- **Notable:** Clean, idiomatic single-file Flask app; goes beyond spec with duplicate-ISBN 409 handling and integer year validation. 37 tests, 0 skipped. One dead helper (`make_test_client`, an unused generator) lingers in the test file.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
