# Evaluation: agent=codex_effort=low_language=elixir_model=gpt-6-luna_prompt=neutral · rep 3

*Second-opinion re-check (2026-10-18) of a prior evaluation that scored requirement_coverage=0.9167.*

## Second-opinion verdict on the prior claim

- **app-not-started — CONFIRMED.** `mix.exs:4-7` defines only `project/0`, and `application: [... mod: {BookApi.Application, []}]` sits inside it. Mix builds the `.app` only from `application/0`, and the file has none (`grep "def application"` finds nothing). Re-run in a temp copy (Elixir 1.20.3 / OTP 29): the generated `_build/dev/lib/book_api/ebin/book_api.app` has no `{mod, ...}` entry, `Application.spec(:book_api, :mod)` = `[]`, `Process.whereis(BookApi.Server)` = `nil`, and connecting to `PORT` returns `{:error, :econnrefused}`. The first evaluator was right.
- **The API code itself is correct.** I started `BookApi.Server.start_link(port: 4792)` by hand and every route behaved: `/health` 200, POST 201, POST without a title 422, `?author=` filter (case-insensitive) 200, GET 200, PUT 200, DELETE 204, then GET 404. So R1–R10 are implemented. The defect is in the startup wiring, and it makes the README's run command (R11) fail.

## Summary

- **Factors:** language=elixir, model=gpt-6-luna, agent=codex, effort=low, prompt=neutral
- **Status:** ok, with a high-severity startup defect
- **Requirements:** 11/12 implemented, 1 partial, 0 missing (pinned REQUIREMENTS.json)
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective). test_coverage=1.0 from scores.json
- **Build:** pass (defect_rate=1.0)
- **Lint:** pass (code_quality=1.0)
- **Architecture:** summary skill not run
- **Findings:** 7 items in `findings.jsonl` (0 critical, 1 high, 3 medium, 2 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books create | ✓ implemented | `server.ex:78-84`, `store.ex:13-16`; manual probe 201 |
| R2 | GET /books list | ✓ implemented | `server.ex:77`, `store.ex:8-11` |
| R3 | ?author= filter | ✓ implemented | `store.ex:9`; test "filters books by author"; probe |
| R4 | GET /books/{id} | ✓ implemented | `server.ex:93-95`; 404 if absent |
| R5 | PUT /books/{id} | ✓ implemented | `server.ex:99-105`, `store.ex:17-20` |
| R6 | DELETE /books/{id} | ✓ implemented | `server.ex:96-98`; probe 204 |
| R7 | SQLite storage | ✓ implemented | `store.ex:30-38` (shells out to the sqlite3 CLI) |
| R8 | JSON + status codes | ✓ implemented | `server.ex:34-36`; 200/201/204/404/422 |
| R9 | title/author validation | ✓ implemented | `server.ex:106-110`; probe 422 |
| R10 | GET /health | ✓ implemented | `server.ex:76` |
| R11 | README setup/run | ~ partial | `README.md:13` `mix run --no-halt` starts nothing (mix.exs defect) |
| R12 | ≥3 tests | ✓ implemented | `test/book_api_test.exs`: 4 tests, all Store-level |

requirement_coverage = 11/12 = 0.9167

## Build & Test

Not re-run: scores.json gives test_coverage=1.0, defect_rate=1.0, code_quality=1.0, maintainability=0.674, idiomatic=0.2. These mechanical scores **overstate** the run, because no test sends a request to the server.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (lib+test) | 296 |
| Files | 6 (.ex/.exs) |
| Dependencies | 0 (sqlite3 CLI required on PATH) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |

## Findings

1. [high] OTP application callback is never registered, so `mix run --no-halt` starts no server (`mix.exs:4-7`)
2. [medium] The README run instruction does not produce a running service
3. [medium] No HTTP-level tests, so the startup defect passed every gate
4. [medium] Create returns the `max(id)` row, so concurrent creates can return the wrong book (`store.ex:39-44`)
5. [low] SQL is built by string interpolation (`store.ex:14,18`)

## Reproduce

```bash
T=$(mktemp -d); cp -R mix.exs lib test $T/; cd $T
BOOKS_DB=$T/b.db PORT=4791 mix run -e 'IO.inspect(Application.spec(:book_api,:mod)); IO.inspect(Process.whereis(BookApi.Server)); IO.inspect(:gen_tcp.connect(~c"127.0.0.1",4791,[]))'
cat _build/dev/lib/book_api/ebin/book_api.app   # no {mod,...}
```
