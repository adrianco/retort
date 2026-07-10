# Architecture Summary — book-api (qwen3-coder-local, typescript/ATDD, rep3)

> Generated inline (the `run-summary` skill was not available in this session).

## Overview

A single-process Express REST API for a book collection, backed by SQLite via
the `sqlite3` (callback) driver. Delivered as plain CommonJS JavaScript despite
the run's `language=typescript` factor (no `.ts` files, no type annotations).

## Modules

| File | Role | Notes |
|------|------|-------|
| `src/server.js` (216 LOC) | The whole app: Express setup, DB init, all routes, 404 + error middleware, conditional `listen()`. Exports `{app, db}` for tests. | Opens its **own** `books.db` handle at import time (`server.js:15`). |
| `src/database.js` (22 LOC) | Standalone DB init + schema; exports `{db, dbPath}`. | **Dead code** — `server.js` never imports it; schema is duplicated. |
| `tests/acceptance.test.js` (314 LOC) | ATDD suite: 12 supertest scenarios exercising the API through HTTP only. | Fails wholesale — see findings. |
| `tests/functional.test.js` | 3 tests: imports server, greps `server.js` for endpoints/status codes, checks `package.json` deps. | Asserts on source text (HOW), not behavior. 1/3 fails (validation regex). |
| `tests/simple.test.js`, `tests/unit.test.js` | Smoke/placeholder tests (`app` defined, module imports, `expect(true).toBe(true)`). | Largely vacuous. |
| `tests/setup.js`, `tests/test-db.js` | Test-DB helpers. | Not imported by any test. |

## HTTP interface

`GET /health` · `POST /books` · `GET /books` (`?author=` filter) ·
`GET /books/:id` · `PUT /books/:id` · `DELETE /books/:id` · catch-all 404.
Status codes: 201/200/400/404/500. Validation: `title` and `author` required.
`isbn` has a UNIQUE constraint (returns 400 on collision — beyond spec).

## Data flow

Request → `express.json()` → route handler → `db.run/get/all` (callback) → JSON
response. DB file is `../books.db` relative to `src/`, created at import.

## Key structural issue

The app is functionally correct at runtime, but the **acceptance suite** — the
artifact the ATDD prompt says *demonstrates the requirements are met* — deletes
the live DB file out from under the open handle in `beforeAll`, so every scenario
crashes with `SQLITE_IOERR`. Even absent that, the scenarios share one persistent
DB with no per-test reset, so they are not atomic/independent.
