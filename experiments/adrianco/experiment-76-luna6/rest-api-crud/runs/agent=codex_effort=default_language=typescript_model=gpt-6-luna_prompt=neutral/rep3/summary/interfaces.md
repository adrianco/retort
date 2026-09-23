# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:"ok"}` | `server.ts:97` |
| GET | /books | `200 [Book]` (opt `?author=` exact filter) | `server.ts:98` |
| POST | /books | `201 Book` \| `400` | `server.ts:103` |
| GET | /books/{id} | `200 Book` \| `404` \| `400` | `server.ts:113` |
| PUT | /books/{id} | `200 Book` \| `404` \| `400` | `server.ts:117` |
| DELETE | /books/{id} | `204` \| `404` \| `400` | `server.ts:125` |

## Library API

- `createApp(databasePath?)` → `http.Server`
- `createBookStore(databasePath)` → `{ create, list, get, update, delete, close }`
- `validateBook(payload)` → `{ value?, error? }`

## Data schema

`books` table (node:sqlite `DatabaseSync`): id (INTEGER PK AUTOINCREMENT), title (TEXT NOT NULL), author (TEXT NOT NULL), year (INTEGER), isbn (TEXT).
