# Run Summary

**Surface:** A REST API for managing a book collection (CRUD over books), built
with Flask and backed by SQLite via the stdlib `sqlite3` module. Exposes create,
list (with author filter), get-by-id, update, delete, and a health check.

- [modules.md](modules.md) — file-level structure
- [interfaces.md](interfaces.md) — HTTP routes and data schema

## Architecture at a glance

Single-module Flask app using the **application-factory** pattern
(`create_app(db_path)`), so tests spin up isolated instances against their own
temporary databases. Persistence is a single `books` table. Request-scoped DB
connections are held on Flask's `g` and closed on teardown. Input validation is
centralized in `validate_book_payload`, shared by POST (full) and PUT (partial).

## Flow

`create_app` → `init_db` (CREATE TABLE IF NOT EXISTS) → route registration.
Each request: handler → `get_db` (open/reuse conn on `g`) → validate (writes) →
SQL → `jsonify` with an explicit status code → teardown closes the connection.
