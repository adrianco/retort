# FunkyGibbon MCP Client Port — Specification

## Overview

This task is to **port the FunkyGibbon MCP client to a new programming language by
extending an existing, real codebase**. Unlike a greenfield build, you start from
a mature multi-language repository (Python + TypeScript reference clients, a shared
protocol spec, ~30K lines) and add a third, conformant implementation.

The client is a **local-first knowledge-graph cache** for a single house: it syncs
an Entity/Relationship graph from the FunkyGibbon server over the *inbetweenies-v2*
protocol, keeps a local copy, and exposes it to LLMs as an **MCP server** with 12
tools. Your port must speak the same protocol on the wire and expose the same 12
tools, so it interoperates with the existing server and is behaviourally
indistinguishable from the reference clients.

---

## The existing repository (you are extending it)

Clone the reference repository at the pinned tag and work inside it:

```bash
git clone https://github.com/adrianco/the-goodies.git
cd the-goodies
git checkout v0.2.2
```

Key things already in the repo — **read them before writing code**:

| Path | What it is |
|------|------------|
| `inbetweenies/PROTOCOL.md` | **The authoritative protocol spec.** Implement *this*, not any one client's quirks. |
| `blowing-off/` | The **Python** reference client (sync engine, local graph, MCP server). |
| `blowing-off/blowingoff/sync/` | Reference sync engine + wire protocol (`engine.py`, `protocol.py`). |
| `blowing-off/blowingoff/mcp/server.py` | Reference **MCP server** (the 12 tools over stdio). |
| `inbetweenies/sync/conflict.py` | The single canonical conflict resolver. |
| `inbetweenies/models/entity.py` | Entity model + version-string format/parse. |
| `funkygibbon/` | The server you sync against (FastAPI). |
| The TypeScript port `rolandcanyon-cmd/the-goodies-typescript` (package `kittenkong`) | A **second reference** — a complete port of the same client, including `src/mcp-server.ts`. |

Add your port as a **new top-level directory** named for the language (e.g.
`wombat-go/`, `wombat-rust/`, …). Do not modify the Python or TypeScript clients;
treat them as the specification-by-example.

---

## What to port (the FunkyGibbon MCP client)

Three layers, matching the reference clients:

1. **Sync client** — speaks inbetweenies-v2 to `POST {server}/api/v1/sync/`:
   pulls server changes, applies them to the local store, pushes local changes,
   resolves conflicts, and advances a persisted delta watermark.
2. **Local graph cache** — stores entities and relationships (an embedded DB or
   equivalent), answers graph queries, and survives restarts.
3. **MCP server** — a stdio MCP server exposing the **12 tools** below, backed by
   the local cache, with an initial sync on startup and background re-sync.

---

## The protocol (inbetweenies-v2) — must match exactly

The full spec is `inbetweenies/PROTOCOL.md`. The load-bearing rules your port
**must** implement:

### Identity & versioning
- An entity has a stable `id` (UUIDv4) and a `version` string. New edits create
  **new immutable versions**; `parent_versions` form a DAG.
- **Version string format:** `{utc-iso8601}-{counter:06d}-{user_id}`, e.g.
  `2026-06-15T09:41:02.581234+00:00-000417-alice`. The timestamp is UTC ISO-8601
  with a `+00:00` offset and **no trailing `Z`**. The counter is a 6-digit
  monotonic per-process tiebreaker. Versions compare **lexically**, and because
  the timestamp prefix is fixed-width UTC, lexical order == chronological order.

### Sync request/response
- `POST /api/v1/sync/` with a `SyncRequest`: `{protocol_version:"inbetweenies-v2",
  device_id, user_id, sync_type:"full"|"delta", changes:[...], filters:{since,
  entity_types?}}`. Bearer-token auth is required.
- The `SyncResponse` returns `{sync_type, changes:[...], conflicts:[...],
  server_time, sync_stats}`.

### Delta watermark (`server_time`)
- After each sync, **persist the response `server_time`** and send it back as
  `filters.since` on the next delta. `since` is an **exclusive** lower bound
  compared against `updated_at` (strictly greater than). Never use the client's
  local clock as the watermark.

### Conflict resolution (one canonical algorithm)
- When the same `id` is edited on both sides: last-write-wins on `updated_at`
  (UTC); if the two `updated_at` are within **1000 ms**, tiebreak on the
  **lexically greater `version`** string. (Not `sync_id` — that field is not on
  the wire.) The server is authoritative and returns the winner in `changes`; the
  client applies it.

### Deletes are tombstones
- A delete is a **new version with `content.deleted = true`** (and the prior
  version as parent), so deletions converge like any other edit. The client treats
  a tombstoned entity as gone but retains the row for sync.

### Timestamps
- All wire timestamps are UTC, timezone-aware, ISO-8601 `+00:00`, microsecond
  precision. Never send naive/local times.

`vector_clock` and `cursor` appear in the schema but are **reserved/unused** —
round-trip them, don't depend on them.

---

## The 12 MCP tools (must match names + behaviour)

Expose these over a stdio MCP server (use the language's MCP SDK if one exists,
else implement the JSON-RPC stdio framing). Names and argument shapes must match
the reference (`blowing-off/blowingoff/mcp/server.py`):

| Tool | Required args | Returns |
|------|---------------|---------|
| `search_entities` | `query` (+ `entity_types?`, `limit?`) | matching entities |
| `get_entity_details` | `entity_id` | entity + all its relationships |
| `create_entity` | `entity_type`, `name`, `content` (+ `user_id?`) | the created entity |
| `update_entity` | `entity_id`, `changes` (+ `user_id?`) | the new version |
| `create_relationship` | `from_entity_id`, `to_entity_id`, `relationship_type` (+ `properties?`, `user_id?`) | the relationship |
| `get_devices_in_room` | `room_id` | devices located in the room |
| `find_device_controls` | `device_id` | controls/automations/procedures for the device |
| `get_room_connections` | `room_id` | doors/windows/passages to adjacent rooms |
| `find_path` | `from_entity_id`, `to_entity_id` (+ `max_depth?`) | the relationship path |
| `find_similar_entities` | `entity_id` (+ `threshold?`, `limit?`) | similar entities |
| `get_procedures_for_device` | `device_id` | procedures/manuals for the device |
| `get_automations_in_room` | `room_id` | automations/schedules for the room |

Entity types: `home, room, device, zone, door, window, procedure, manual, note,
schedule, automation, app`.

---

## Provided fixtures (in `fixtures/`)

Self-contained test data so the port can be built and verified without a live
server. **Your port must satisfy these** (they encode the protocol rules above):

- `knowledge-graph.json` — a small entity/relationship snapshot (a house with
  rooms, devices, a door, a procedure with a tombstoned old version).
- `sync-exchanges.json` — golden `SyncRequest → SyncResponse` pairs covering:
  full sync, a delta with `since`, a concurrent-edit conflict resolved by version
  tiebreak, and a tombstone delete propagating.
- `version-strings.json` — valid/invalid version strings + their parsed UTC
  timestamps and the expected lexical ordering (test your formatter + parser +
  comparator against these).
- `mcp-tool-golden.json` — a few tool calls against `knowledge-graph.json` with
  their expected results (e.g. `get_devices_in_room`, `find_path`,
  `search_entities`).

---

## Required capabilities (what is scored)

1. Speaks inbetweenies-v2: builds a valid `SyncRequest` and parses `SyncResponse`,
   round-tripping reserved fields.
2. Version strings: formats and parses the canonical format (no doubled `Z`,
   6-digit counter) and orders them lexically == chronologically.
3. Delta watermark: persists `server_time` and replays it as an **exclusive**
   `since`; does not use the local clock.
4. Conflict resolution: the canonical LWW + 1s/version-tiebreak algorithm.
5. Tombstone deletes: applies and represents `content.deleted = true` versions.
6. Local graph cache: stores entities/relationships durably and answers the graph
   queries the tools need.
7. MCP server: serves all **12 tools** over stdio with the matching names/args;
   initial sync on startup + background re-sync.
8. Bearer-token auth on sync requests.
9. Passes the provided `fixtures/` (version strings, sync exchanges, tool golden).
10. Automated tests covering the above; they build and run in the target language.
11. A README explaining how to build, test, and run the MCP server.

---

## Deliverables

- A new `*/` directory in the repo containing the port's source, written
  idiomatically in the target language and matching the repo's structure.
- Passing automated tests (in the target language's framework).
- A README with build/test/run instructions and the MCP-server config snippet.
- The Python and TypeScript clients left unmodified.

## Success criteria

- **Conformance:** satisfies every rule in `inbetweenies/PROTOCOL.md` exercised by
  the fixtures; the version formatter/parser/comparator, the conflict resolver,
  and the tombstone logic match the golden fixtures exactly.
- **Interop:** the MCP server lists exactly the 12 tools with the correct
  names/argument schemas; a tool call returns the expected shape.
- **Tests pass** in the target language.

## References

- `inbetweenies/PROTOCOL.md` — the spec (authoritative).
- `blowing-off/` — Python reference client (incl. `blowingoff/mcp/server.py`).
- `rolandcanyon-cmd/the-goodies-typescript` (`kittenkong`) — TypeScript reference.
- Model Context Protocol: https://modelcontextprotocol.io
