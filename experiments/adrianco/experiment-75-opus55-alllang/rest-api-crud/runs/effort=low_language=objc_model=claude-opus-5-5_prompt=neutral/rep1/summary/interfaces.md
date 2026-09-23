# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:ok}` | `BookAPI.m:handleMethod` (86–87) |
| POST | /books | `201 Book \| 400` | `BookAPI.m:handleMethod` (98–109) |
| GET | /books | `200 [Book]` (optional `?author=` exact filter) | `BookAPI.m:handleMethod` (90–96) |
| GET | /books/{id} | `200 Book \| 404 \| 400` | `BookAPI.m:handleMethod` (117–118) |
| PUT | /books/{id} | `200 Book \| 404 \| 400` | `BookAPI.m:handleMethod` (119–131) |
| DELETE | /books/{id} | `204 \| 404` | `BookAPI.m:handleMethod` (132–138) |

Unknown methods on a known path return `405`; unknown paths return `404`.

## Library API

- `BAResponse` — `status` (NSInteger), `body` (NSData), `-json` decodes body.
- `BookAPI` — `-initWithDatabasePath:` (accepts `":memory:"`), `-handleMethod:target:body:`.
- `BARunServer(BookAPI *, int port)` — blocking accept loop, one request per connection.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER), `isbn` (TEXT). Defined in `BookAPI.m:24–25`.
