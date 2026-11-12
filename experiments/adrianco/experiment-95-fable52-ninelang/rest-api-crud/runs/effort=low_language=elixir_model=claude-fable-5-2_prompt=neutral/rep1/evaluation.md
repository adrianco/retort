# Evaluation: rest-api-crud · effort=low language=elixir model=claude-fable-5-2 prompt=neutral · rep 1

## Summary

- **Factors:** language=elixir, model=claude-fable-5-2, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 12 passed / 0 failed / 0 skipped (12 effective) — from `test_coverage=1.0` (scores.json)
- **Build:** pass — `test_coverage=1.0` implies compile + tests succeeded (not re-run per skill)
- **Lint:** pass — `code_quality=1.0` (scores.json)
- **Architecture:** Plug + Bandit HTTP server, GenServer-owned SQLite (exqlite) store, pure validation module; summary skill not run (unavailable in this session)
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `router.ex:27 post "/books"` → `Store.create/1` (`store.ex:62`); test "POST /books creates a book" |
| R2 | GET /books lists all | ✓ implemented | `router.ex:16 get "/books"` → `Store.list/1`; test "GET /books lists all books" |
| R3 | GET /books ?author= filter | ✓ implemented | `router.ex:19` builds `%{author:}`; `store.ex:46` `WHERE author = ?1`; test filters by author |
| R4 | GET /books/{id} single (404) | ✓ implemented | `router.ex:36 get "/books/:id"`; `parse_id` + `Store.get`; test returns 404 for unknown/invalid |
| R5 | PUT /books/{id} updates | ✓ implemented | `router.ex:43 put "/books/:id"`; `Store.update/2` (`store.ex:72`); test "PUT updates a book" |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `router.ex:54 delete "/books/:id"`; `Store.delete/1`; test "DELETE removes a book" (204 + 404 after) |
| R7 | SQLite / embedded DB | ✓ implemented | `store.ex` uses `Exqlite.Sqlite3`, `CREATE TABLE books`, parameterized SQL |
| R8 | JSON + appropriate codes | ✓ implemented | `json/3` sets `application/json`; 201/200/204/404/400/413/422 across routes (see low finding on 422) |
| R9 | title & author required | ✓ implemented | `book.ex:9 validate/1`, `required_string`; test "validates required fields" rejects missing/blank |
| R10 | GET /health | ✓ implemented | `router.ex:12 get "/health"` → `{status: "ok"}`; test "GET /health" |
| R11 | README with setup/run | ✓ implemented | `README.md` — setup (`mix deps.get`), run, env vars, tests, full API table |
| R12 | ≥3 tests | ✓ implemented | 12 tests in `test/book_api_test.exs`, all pass (`test_coverage=1.0`) |

All requirements satisfied. The only deviation is cosmetic: validation failures return **422** where `REQUIREMENTS.json` R9's `how_to_verify` names **400** (the request is still correctly rejected). Two enhancements beyond spec: a `Location` header on create and a request-body size limit (413).

## Build & Test

Not re-run — stored scores from `scores.json` used per the evaluate-run skill:

```text
code_quality=1.0  test_coverage=1.0  defect_rate=1.0
maintainability=0.845  idiomatic=0.88  token_efficiency=0.0
```

`test_coverage=1.0` ⇒ `mix test` compiled and all 12 tests passed. No skipped/`@tag :skip` tests found.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (lib/ source only) | 296 |
| Files (excl. build/logs/meta) | 15 |
| Dependencies | 3 (plug, bandit, exqlite) |
| Tests total | 12 |
| Tests effective | 12 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Validation failures return 422 rather than the spec's 400 — `router.ex:71`
2. [info] POST /books sets a Location header on 201 (enhancement) — `router.ex:30`
3. [info] Request body size limit with 413 response (enhancement) — `router.ex:94`

## Reproduce

```bash
cd "experiments/adrianco/experiment-95-fable52-ninelang/rest-api-crud/runs/effort=low_language=elixir_model=claude-fable-5-2_prompt=neutral/rep1"
cat scores.json                         # stored mechanical scores (build/test/lint)
cat ../../REQUIREMENTS.json             # pinned 12-requirement checklist
mix deps.get && mix test                # optional: reproduce the 12 passing tests
```
