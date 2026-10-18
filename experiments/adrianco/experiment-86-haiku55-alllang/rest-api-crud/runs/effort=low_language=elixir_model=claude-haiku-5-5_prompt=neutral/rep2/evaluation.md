# Evaluation: effort=low language=elixir model=claude-haiku-5-5 prompt=neutral · rep 2

## Summary

- **Factors:** language=elixir, model=claude-haiku-5-5, effort=low, prompt=neutral (agent/framework unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 8 passed / 0 failed / 0 skipped (8 effective) — from `test_coverage=1.0`
- **Build:** pass (via `test_coverage=1.0` in scores.json — build+tests ran)
- **Lint:** pass — `code_quality=1.0` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

## Requirements

Checklist pinned from `../../REQUIREMENTS.json` (12 fixed requirements).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates book (title, author, year, isbn) | ✓ implemented | `router.ex:21`, `book.ex:28` create + INSERT; test `books_api_test.exs:39` |
| R2 | GET /books lists all | ✓ implemented | `router.ex:28`, `book.ex:11` list; test `:50` |
| R3 | GET /books ?author= filter | ✓ implemented | `book.ex:13-15` WHERE author = ?; `router.ex:29`; test `:67` |
| R4 | GET /books/{id}, 404 if absent | ✓ implemented | `router.ex:35`, `book.ex:20`; test `:46`, `:64` |
| R5 | PUT /books/{id} updates | ✓ implemented | `router.ex:44`, `book.ex:45`; test `:54` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `router.ex:55`, `book.ex:60`; test `:61`, `:105` |
| R7 | Data stored in SQLite | ✓ implemented | `repo.ex:7` Exqlite.Sqlite3, `:40` CREATE TABLE books |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `router.ex:80-84` JSON; 201/200/404/204/422/400 across routes |
| R9 | Validation: title and author required | ✓ implemented | `book.ex:68-104` require_string; test `:76`, `:84` (returns 422 — see finding) |
| R10 | GET /health | ✓ implemented | `router.ex:17`; test `:33` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` Setup/Run/Test/API sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | 8 tests in `books_api_test.exs`; `test_coverage=1.0` |

## Build & Test

Scores read from `scores.json` (inline gate scores — build/tests NOT re-run per skill §2):

```text
{"code_quality": 1.0, "token_efficiency": 0.0, "test_coverage": 1.0,
 "defect_rate": 1.0, "maintainability": 0.8143, "idiomatic": 0.62}
```

`test_coverage=1.0` ⇒ `mix test` built the project and all tests passed.
`defect_rate=1.0` ⇒ build+test succeeded. No skipped/disabled tests detected
(`grep` for `@tag :skip` / skip returned none).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, .ex/.exs) | 403 |
| Lines of code (lib only) | 279 |
| Files (lib+test+config) | 9 |
| Dependencies (mix.exs) | 4 (plug, bandit, jason, exqlite) |
| Tests total | 8 |
| Tests effective | 8 |
| Skip ratio | 0% |
| Build/test | pass (test_coverage=1.0) |

## Findings

Full list in `findings.jsonl`:

1. [low] R9 — validation failures return 422 while the spec names 400 (`router.ex:77`). 422 is a defensible choice; internally consistent and documented in README.
2. [info] PUT performs a full replace, clearing omitted optional fields (`book.ex:45`); documented in README, noted for cross-run comparison.

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=elixir_model=claude-haiku-5-5_prompt=neutral/rep2"
cat scores.json                 # stored build/test/lint scores (not re-run)
cat ../../REQUIREMENTS.json      # pinned 12-requirement checklist
# optional, to re-verify locally (NOT required — scores are authoritative):
# mix deps.get && mix test
```
