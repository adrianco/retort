# Architecture Summary: Books API (TypeScript/Express)

## Modules

| File | Role | Lines |
|------|------|-------|
| `src/app.ts` | Express app factory — routes, validation, error handler | 148 |
| `src/db.ts` | Database module — Book interface, SQLite schema, connection factory | 24 |
| `src/server.ts` | Entry point — reads env vars, wires DB + app, starts listener | 12 |
| `tests/books.test.ts` | Integration tests — supertest against in-memory DB | 162 |
| `jest.config.js` | Jest config with ts-jest preset | 6 |

## Interfaces

- **Book** (`src/db.ts:3-9`): `{ id, title, author, year?, isbn? }` — the domain entity
- **BookInput** (`src/app.ts:5-10`): Raw request body shape before validation
- **validateBookInput** (`src/app.ts:12-47`): Pure validation function returning discriminated union (`{ok: true, data}` | `{ok: false, error}`)

## Data Flow

1. `server.ts` creates a file-backed SQLite DB via `createDb('books.db')` and passes it to `createApp(db)`
2. `createApp` returns an Express app with JSON middleware and six routes
3. Each route uses the injected `db` directly (prepared statements, no ORM)
4. Tests call `createApp(createDb(':memory:'))` for isolated in-memory instances per test

## Key Design Decisions

- **Dependency injection**: `createApp(db)` accepts a DB instance, enabling test isolation without mocking
- **No ORM**: Raw better-sqlite3 prepared statements — minimal abstraction for a small schema
- **WAL mode**: `db.ts:13` enables WAL journal for better concurrent read performance
- **Validation as pure function**: `validateBookInput` is separate from route handlers, testable in isolation
