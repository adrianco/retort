# Evaluation: rest-api-crud · effort=low language=elixir model=claude-haiku-5-5 prompt=neutral · rep 3

## Summary

- **Factors:** language=elixir, model=claude-haiku-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 13 passed / 0 failed / 0 skipped (13 effective)
- **Build:** pass (test_coverage=1.0 from scores.json ⇒ build + all tests passed)
- **Lint:** pass (code_quality=1.0 from scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

Stored scores (`scores.json`): test_coverage=1.0, code_quality=1.0, defect_rate=1.0, maintainability=0.96, idiomatic=0.85, token_efficiency=0.0. Run cost $0.0108, 7 turns (`_agent_stdout.log`).

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `router.ex:17` → `Books.create_book`; test `router_test.exs:36` |
| R2 | GET /books lists all | ✓ implemented | `router.ex:24`; `books.ex:7 list_books` |
| R3 | GET /books ?author= filter | ✓ implemented | `router.ex:25` passes query_params; `books.ex:26 maybe_filter_author`; test `router_test.exs:76` |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `router.ex:29`; test `router_test.exs:87` |
| R5 | PUT /books/{id} updates | ✓ implemented | `router.ex:38`; `books.ex:20`; test `router_test.exs:52` |
| R6 | DELETE /books/{id} | ✓ implemented | `router.ex:50` → 204; test `router_test.exs:56` |
| R7 | Stored in SQLite | ✓ implemented | `repo.ex` `Ecto.Adapters.SQLite3`; `mix.exs` `ecto_sqlite3`; migration present |
| R8 | JSON + appropriate status codes | ✓ implemented | `router.ex:100 json/3`; 201/200/204/404/422 used |
| R9 | title & author required | ✓ implemented | `book.ex:22 validate_required`; test `router_test.exs:62` (returns 422 — see findings) |
| R10 | GET /health | ✓ implemented | `router.ex:13`; test `router_test.exs:30` |
| R11 | README with setup/run | ✓ implemented | `README.md` (setup, run, test, endpoints, examples) |
| R12 | ≥ 3 tests | ✓ implemented | 13 tests (8 router + 5 context); test_coverage=1.0 |

## Build & Test

Not re-run — stored scores used per skill policy.

```text
scores.json: {"code_quality": 1.0, "token_efficiency": 0.0, "test_coverage": 1.0,
              "defect_rate": 1.0, "maintainability": 0.9596, "idiomatic": 0.85}
```

```text
13 tests, 0 failures, 0 skipped (_agent_stdout.log: "mix test passes: 13 tests")
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (lib) | 188 |
| Lines of code (test) | 162 |
| Files (lib/test/priv/config) | 13 |
| Dependencies (mix.exs) | 4 |
| Tests total | 13 |
| Tests effective | 13 |
| Skip ratio | 0% |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] R9 validation rejects with 422 rather than the 400 hinted in the task — correct per HTTP semantics; requirement satisfied.
2. [info] Transient "database is locked" seen once during dev DB setup — not reproduced; test suite unaffected.

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=elixir_model=claude-haiku-5-5_prompt=neutral/rep3"
cat scores.json
grep -cE '^\s*test "' test/book_api/*.exs
mix test   # (optional — stored test_coverage=1.0)
```
