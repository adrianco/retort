# Evaluation: agent=codex model=gpt-5.6-terra language=elixir prompt=neutral · rep 1

## Summary

- **Factors:** language=elixir, model=gpt-5.6-terra, agent=codex, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned REQUIREMENTS.json)
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective) — `test_coverage=1.0` from scores.json
- **Build:** pass — `test_coverage=1.0` implies build + all tests ran (not re-run)
- **Lint:** pass — `code_quality=0.9167` from scores.json
- **Architecture:** run-summary skill unavailable in this environment — see module notes below
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `lib/book_api/router.ex:7`, `store.ex:17` INSERT ... RETURNING → 201 |
| R2 | GET /books lists all | ✓ implemented | `router.ex:5`, `store.ex:10-13` |
| R3 | GET /books ?author= filter | ✓ implemented | `router.ex:5` passes `query["author"]`; `store.ex:11` WHERE author= |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `router.ex:6,12-17` fetch → 200/404; test line 35 |
| R5 | PUT /books/{id} updates | ✓ implemented | `router.ex:8,18-23`; `store.ex:21-24`; test line 33 |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `router.ex:9,24-29` → 204; test line 34 |
| R7 | Data in SQLite / embedded DB | ✓ implemented | `store.ex:6` CREATE TABLE, `store.ex:35,44` sqlite3; not in-memory |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `server.ex:55-65` JSON body + 200/201/204/404/422 (validation uses 422 vs conventional 400 — see finding R8) |
| R9 | Validation: title & author required | ✓ implemented | `router.ex:40-52`; test line 27 rejects missing title |
| R10 | GET /health | ✓ implemented | `router.ex:4` → `{200, %{status: "ok"}}`; test line 28 |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — Run/Endpoints/Test sections |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | `test/book_api_test.exs` — 4 tests, `test_coverage=1.0` |

## Build & Test

Not re-run per skill guidance — stored mechanical scores are authoritative:

```text
scores.json
test_coverage = 1.0    → build succeeded + all tests passed
code_quality  = 0.9167
defect_rate   = 0.7419
```

Tests exercise the router handler directly (`config/test.exs` sets `port: 0` so no socket is bound); each test uses an isolated temp SQLite DB (`test/book_api_test.exs:5-9`). No skipped/disabled tests (grep for `@tag :skip` → 0).

Note: the agent's stderr shows one blocked command — an `rm -rf`-style precompile step was rejected by the sandbox (`_agent_stderr.log`) — but this did not affect the final workspace or the passing test run.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, lib+test+mix+config) | 342 |
| Source files (lib) | 5 |
| Dependencies (Hex) | 0 (stdlib only + sqlite3 CLI) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | not re-run (test_coverage=1.0) |

## Architecture (run-summary unavailable)

Umbrella-free Mix app, no Hex deps. Layers:
- `application.ex` — supervises a `Task.Supervisor` + `Server`, runs `Store.setup/0` at boot.
- `server.ex` — hand-rolled HTTP/1.1 over `:gen_tcp`, parses request line + Content-Length body, dispatches to `Router.route/4`, serializes responses.
- `router.ex` — pattern-matched routing, ID/body validation, maps to `{status, payload}`.
- `store.ex` — SQLite persistence via `System.cmd("sqlite3", ...)` with interpolated (single-quote-escaped) SQL.
- `json.ex` — self-contained JSON encode/decode (no deps).

## Findings

Top items (full list in `findings.jsonl`):

1. [low] Validation failures return 422 instead of the conventional 400 (`router.ex:37`)
2. [low] SQL built via string interpolation rather than parameterized queries (`store.ex:11,18,22`; escaping mitigates injection)
3. [info] Persistence shells out to the sqlite3 CLI binary rather than a library driver (`store.ex:35,44`)

No critical/high/medium findings — the run fully implements the spec, all tests pass, and there are no skipped tests.

## Reproduce

```bash
cd "experiments/adrianco/experiment-56-terra-alllang/bookshop/runs/agent=codex_effort=default_language=elixir_model=gpt-5.6-terra_prompt=neutral/rep1"
cat scores.json                       # stored build/test/lint scores (authoritative)
grep -rE "@tag :skip" test/ | wc -l   # 0 skipped tests
# To re-verify locally (optional): mix test
```
