# Evaluation: rest-api-crud · effort=low language=elixir model=claude-haiku-5-5 prompt=neutral · rep 1

## Summary

- **Factors:** language=elixir, model=claude-haiku-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 13 passed / 0 failed / 0 skipped (13 effective)
- **Build:** pass — from `test_coverage=1.0` (retort.db / scores.json)
- **Lint:** pass — `code_quality=1.0` (scores.json)
- **Architecture:** Plug/Bandit router → `Books` context (validation + persistence) → `DB` GenServer serializing a single SQLite (`exqlite`) connection
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

Checklist is the pinned `rest-api-crud/REQUIREMENTS.json` (12 items, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `router.ex:20` → `books.ex:13 create/1` INSERTs 4 fields, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `router.ex:24` → `books.ex:22 list/1` SELECT ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `books.ex:24-27` WHERE author = ? COLLATE NOCASE; `router_test.exs:58` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `router.ex:29` → `books.ex:35 get/1`; `:not_found`→404 `router.ex:49` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `router.ex:33` → `books.ex:44 update/1`; `router_test.exs:43` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `router.ex:37-42` → `books.ex:57 delete/1`, 204; `router_test.exs:47` |
| R7 | Data stored in SQLite/embedded DB | ✓ implemented | `db.ex` Exqlite.Sqlite3, CREATE TABLE books, file at `data/book_api.db` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `router.ex:64-68 json/3`; 201/200/204/404/422/400/500 |
| R9 | Validation: title & author required | ✓ implemented | `books.ex:83-100 field_errors`; `router_test.exs:51` (422). See finding R9 |
| R10 | GET /health health check | ✓ implemented | `router.ex:13-18` runs `SELECT 1`, 200/503; `router_test.exs:29` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — Setup/Run/Test/API sections |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 13 tests (6 router + 7 books), 0 skipped; `test_coverage=1.0` |

## Build & Test

Not re-run — stored mechanical scores used per skill (compiled toolchain, avoid duplication):

```text
scores.json: test_coverage=1.0  code_quality=1.0  defect_rate=1.0
             maintainability=0.886  idiomatic=0.8  token_efficiency=0.0
```

`test_coverage=1.0` ⇒ `mix test` built and all tests passed. 13 tests, 0 skips.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source + test, .ex/.exs) | 475 |
| Files (lib/test/config) | 8 |
| Dependencies (mix.exs) | 4 (plug, bandit, exqlite, jason) |
| Tests total | 13 |
| Tests effective | 13 |
| Skip ratio | 0% |
| Build/test | pass (test_coverage=1.0) |

## Findings

Full list in `findings.jsonl` — all informational, no defects:

1. [info] R9 — validation returns 422 (not the 400 named in the verify note); 422 is an appropriate rejection code, requirement satisfied.
2. [info] R3 — `?author=` filter is case-insensitive (COLLATE NOCASE), a small enhancement over the bare spec.

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=elixir_model=claude-haiku-5-5_prompt=neutral/rep1"
cat scores.json          # stored mechanical scores (build/test/lint)
grep -rE "^\s*test " test/ | wc -l   # 13 tests
grep -rE "@tag :skip|:skip\]" test/  # 0 skips
# full build/test (optional, already scored): mix deps.get && mix test
```
