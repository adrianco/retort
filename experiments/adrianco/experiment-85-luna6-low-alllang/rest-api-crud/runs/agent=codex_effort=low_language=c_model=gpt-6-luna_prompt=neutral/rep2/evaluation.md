# Evaluation: agent=codex effort=low language=c model=gpt-6-luna prompt=neutral · rep 2

## Summary

- **Factors:** language=c, model=gpt-6-luna, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective) — from `scores.json` test_coverage=1.0
- **Build:** pass (from scores.json test_coverage=1.0; also binary `book_server` present) — not re-run
- **Lint:** pass — code_quality=0.956 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 3 low)

Scores read from `scores.json` (inline gate; not re-run per evaluate-run skill):
`test_coverage=1.0`, `code_quality=0.956`, `defect_rate=1.0`, `maintainability=1.0`,
`idiomatic=0.1`, `token_efficiency=0.0047`.

## Requirements

Checklist pinned from `rest-api-crud/REQUIREMENTS.json` (12 fixed items).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `server.c:50` INSERT, returns 201 + record |
| R2 | GET /books lists all | ✓ implemented | `server.c:44` SELECT … ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `server.c:44` `WHERE author=?` bound from query arg |
| R4 | GET /books/{id} single (404) | ✓ implemented | `server.c:46` SELECT by id, 404 if no row |
| R5 | PUT /books/{id} update | ✓ implemented | `server.c:48` UPDATE, 404 if unchanged, returns record |
| R6 | DELETE /books/{id} | ✓ implemented | `server.c:47` DELETE, 404 if no change |
| R7 | Data stored in SQLite | ✓ implemented | `server.c:55` sqlite3_open + CREATE TABLE books |
| R8 | JSON responses + status codes | ✓ implemented | `send_response`/`error_response` (server.c:23-24); 201/200/400/404/413/500 |
| R9 | Validate title & author required | ✓ implemented | `server.c:48,50` reject with 400 when empty |
| R10 | GET /health | ✓ implemented | `server.c:43` returns `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` — deps, `make`, run, API, tests |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test_server.c` 3 test groups, test_coverage=1.0 |

No requirements missing or partial. Enhancement beyond spec: CORS headers + `OPTIONS`
handling (server.c:23,51), request-body size cap with 413 (server.c:42).

## Build & Test

Not re-run — stored scores used per the evaluate-run skill.

```text
scores.json: test_coverage=1.0  => make test built book_server + test_server and all tests passed
scores.json: code_quality=0.9556 (lint pass)
make test -> ./test_server -> "3 tests passed: validation parser, create/filter/serialize, update/delete"
```

Tests (`test_server.c`) cover: (1) `parse_fields` parsing + missing-author handling,
(2) SQLite insert + author-filter SELECT + `serialize_book` output, (3) UPDATE then
DELETE with `sqlite3_changes` assertions. They do not drive `handler()` over HTTP
(see finding `test-e2e`).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 115 (server.c 56, test_server.c 44, Makefile 15) |
| Files (excl. binary/.git) | server.c, test_server.c, Makefile, README.md, TASK.md, stack.json |
| Dependencies | libmicrohttpd, sqlite3 (via pkg-config) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — none above low severity:

1. [low] Tests cover helpers directly, not the HTTP handler end-to-end (`test_server.c`)
2. [low] Fixed 4096/20000-byte stack buffers truncate long fields silently (`server.c:38`)
3. [low] Unchecked `realloc` in GET /books list builder (`server.c:44`)

## Reproduce

```bash
cd "/Users/adriancockcroft/code/retort/experiments/adrianco/experiment-85-luna6-low-alllang/rest-api-crud/runs/agent=codex_effort=low_language=c_model=gpt-6-luna_prompt=neutral/rep2"
cat scores.json                 # stored mechanical scores (build/test/lint)
cat REQUIREMENTS.json           # ../../../REQUIREMENTS.json — pinned 12-item checklist
make test                       # (optional) rebuild + rerun C tests
```
